#!/usr/bin/env python3
"""Promote an ingested capture batch to a reference dataset version.

Usage:
  python scripts/promote_capture_batch_to_dataset.py --batch lab_lv_monogram_batch_001 --dataset lab_lv_monogram_v0.1.0 [--activate]
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
import psycopg2

# Import embedding function
_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)
compute_texture_embedding = _imaging.compute_texture_embedding
normalize_image = _imaging.normalize_image

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
S3_ENDPOINT = "http://localhost:4566"
EMBEDDING_MODEL = "texture_baseline_v0.1.0"
EMBEDDING_DIM = 128


def get_s3():
    return boto3.client("s3", endpoint_url=S3_ENDPOINT, aws_access_key_id="test",
                        aws_secret_access_key="test", region_name="us-east-1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source-type", default="lab_curated")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    s3 = get_s3()
    now = datetime.now(timezone.utc)

    # Check batch
    cur.execute("SELECT id, status FROM capture_batches WHERE batch_code = %s", (args.batch,))
    batch_row = cur.fetchone()
    if not batch_row:
        print(f"Batch not found: {args.batch}")
        sys.exit(1)
    batch_id, status = batch_row
    if status != "INGESTED":
        print(f"Batch must be INGESTED, got '{status}'")
        sys.exit(1)

    # Create or get dataset version
    ds_status = "active" if args.activate else "draft"
    cur.execute("SELECT id FROM reference_dataset_versions WHERE dataset_version = %s", (args.dataset,))
    ds_row = cur.fetchone()
    if ds_row:
        ds_id = ds_row[0]
        print(f"Using existing dataset version: {args.dataset}")
    else:
        ds_id = str(uuid.uuid4())
        cur.execute("""INSERT INTO reference_dataset_versions (id, dataset_version, description, source_type, status, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (ds_id, args.dataset, f"Promoted from batch {args.batch}",
                     args.source_type, ds_status, now, now))
        print(f"Created dataset version: {args.dataset} (status={ds_status})")

    # Get items with their external_item_ids for split assignment
    cur.execute("""SELECT DISTINCT bi.external_item_id
                   FROM capture_batch_items bi
                   WHERE bi.capture_batch_id = %s
                   ORDER BY bi.external_item_id""", (str(batch_id),))
    item_ids = [r[0] for r in cur.fetchall()]

    # Assign splits by item (all images from same item stay in same split)
    splits_cycle = ["train", "train", "train", "validation", "test"]
    item_splits = {}
    for i, ext_id in enumerate(item_ids):
        item_splits[ext_id] = splits_cycle[i % len(splits_cycle)]

    print(f"Split assignment: {dict((k, v) for k, v in item_splits.items())}")

    # Leakage check: collect SHA-256 by split
    sha_by_split = {"train": set(), "validation": set(), "test": set()}

    # Get all reference images from this batch
    cur.execute("""SELECT cbi.id, cbi.external_image_id, cbi.sha256_checksum, cbi.region_code,
                          cbi.capture_batch_item_id, bitem.external_item_id, cbi.normalized_object_uri
                   FROM capture_batch_images cbi
                   JOIN capture_batch_items bitem ON bitem.id = cbi.capture_batch_item_id
                   WHERE cbi.capture_batch_id = %s AND cbi.status = 'INGESTED'""", (str(batch_id),))
    batch_images = cur.fetchall()

    leakage_warnings = []
    promoted = 0

    for img_id, ref_image_id, sha256, region_code, _, ext_item_id, norm_uri in batch_images:
        if not ref_image_id:
            continue

        split = item_splits.get(ext_item_id, "train")

        # Leakage check
        if sha256:
            for other_split, other_shas in sha_by_split.items():
                if other_split != split and sha256 in other_shas:
                    leakage_warnings.append(f"SHA-256 {sha256[:16]}... in both {split} and {other_split}")
            sha_by_split[split].add(sha256)

        # Set flags based on split
        in_search = split in ("train",)
        in_eval = split in ("validation", "test")
        in_training = split == "train"

        # Add to dataset members
        cur.execute("""INSERT INTO reference_dataset_members (id, dataset_version_id, reference_image_id, split, include_in_search, include_in_evaluation, include_in_training)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (str(uuid.uuid4()), str(ds_id), str(ref_image_id), split, in_search, in_eval, in_training))

        # Generate and store embedding
        if norm_uri:
            try:
                parts = norm_uri.replace("s3://", "").split("/", 1)
                resp = s3.get_object(Bucket=parts[0], Key=parts[1])
                norm_bytes = resp["Body"].read()
                embedding = compute_texture_embedding(norm_bytes, dim=EMBEDDING_DIM)
                vec_str = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
                cur.execute("""INSERT INTO reference_embeddings (id, reference_image_id, embedding, embedding_model_version)
                               VALUES (%s, %s, %s::vector, %s)
                               ON CONFLICT DO NOTHING""",
                            (str(uuid.uuid4()), str(ref_image_id), vec_str, EMBEDDING_MODEL))
            except Exception as exc:
                print(f"  WARN: embedding failed for {ref_image_id}: {exc}")

        promoted += 1

    # Update batch
    cur.execute("UPDATE capture_batches SET status = 'PROMOTED', dataset_candidate_name = %s, updated_at = %s WHERE id = %s",
                (args.dataset, now, str(batch_id)))

    # Audit
    leakage_summary = {"warnings": leakage_warnings, "count": len(leakage_warnings)}
    cur.execute("INSERT INTO audit_events (id, event_type, payload, created_at) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), "DATASET_LEAKAGE_CHECK_COMPLETED", json.dumps(leakage_summary), now))
    cur.execute("INSERT INTO audit_events (id, event_type, payload, created_at) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), "CAPTURE_BATCH_PROMOTED_TO_DATASET",
                 json.dumps({"batch_code": args.batch, "dataset": args.dataset, "promoted": promoted}), now))

    # Report
    print(f"\nPromoted {promoted} images from batch {args.batch} to dataset {args.dataset}")
    print(f"Dataset status: {ds_status}")
    splits_count = {}
    for s in item_splits.values():
        splits_count[s] = splits_count.get(s, 0) + 1
    print(f"Item splits: {splits_count}")
    if leakage_warnings:
        print(f"\nLeakage warnings ({len(leakage_warnings)}):")
        for w in leakage_warnings:
            print(f"  - {w}")
    else:
        print("Leakage check: clean")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
