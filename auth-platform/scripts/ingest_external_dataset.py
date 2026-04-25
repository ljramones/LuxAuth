#!/usr/bin/env python3
"""Ingest an external public dataset into the LuxAuth backend.

Usage:
  python scripts/ingest_external_dataset.py --manifest ../datasets/manifests/leadata-manifest.yaml --dry-run
  python scripts/ingest_external_dataset.py --manifest ../datasets/manifests/leadata-manifest.yaml --force
"""

import argparse
import importlib
import importlib.util
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import psycopg2
import yaml

# Import imaging
_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)
normalize_image = _imaging.normalize_image
compute_texture_embedding = _imaging.compute_texture_embedding
validate_image = _imaging.validate_image

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
S3_ENDPOINT = "http://localhost:4566"
S3_BUCKET = "auth-platform-reference-library"
EMBEDDING_MODEL = "texture_baseline_v0.1.0"
EMBEDDING_DIM = 128

ADAPTER_MAP = {
    "LeaData": "external_adapters.leadata_adapter",
    "FabricNET": "external_adapters.fabricnet_adapter",
}

SPLITS = ["train", "train", "train", "validation", "test"]
SAFE_PREFIXES = ("external_", "synthetic_", "smoke_")


def get_s3():
    return boto3.client("s3", endpoint_url=S3_ENDPOINT, aws_access_key_id="test",
                        aws_secret_access_key="test", region_name="us-east-1")


def get_split_flags(split):
    if split == "train":
        return True, False, True
    return False, True, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path to manifest YAML")
    parser.add_argument("--dataset-version", default=None, help="Override dataset version")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace existing external dataset")
    parser.add_argument("--allow-commercial-flag", action="store_true",
                        help="Required if manifest says commercial_use_allowed=true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Validate manifest
    source_type = manifest.get("source_type")
    if source_type != "public_external":
        print(f"ERROR: source_type must be 'public_external', got '{source_type}'")
        sys.exit(1)

    if manifest.get("commercial_use_allowed") and not args.allow_commercial_flag:
        print("ERROR: commercial_use_allowed=true requires --allow-commercial-flag")
        sys.exit(1)

    dataset_name = manifest.get("dataset_name")
    dataset_version = args.dataset_version or manifest.get("dataset_version")
    if not dataset_version:
        print("ERROR: dataset_version required in manifest or via --dataset-version")
        sys.exit(1)

    if not dataset_version.startswith("external_"):
        print(f"WARNING: dataset_version '{dataset_version}' does not start with 'external_'")

    # Resolve local path relative to repo root
    local_path = manifest.get("local_path", "")
    repo_root = Path(__file__).parent.parent.parent  # auth-platform/../
    resolved_path = (repo_root / local_path).resolve()
    print(f"Dataset: {dataset_name}")
    print(f"Version: {dataset_version}")
    print(f"Local path: {resolved_path}")

    if not resolved_path.exists():
        print(f"ERROR: Local path does not exist: {resolved_path}")
        print("Download the dataset first and place it at the expected path.")
        sys.exit(1)

    # Load adapter
    adapter_module = ADAPTER_MAP.get(dataset_name)
    if not adapter_module:
        print(f"ERROR: No adapter for dataset '{dataset_name}'. Available: {list(ADAPTER_MAP.keys())}")
        sys.exit(1)

    # Import adapter from scripts/external_adapters/
    sys.path.insert(0, str(Path(__file__).parent))
    adapter = importlib.import_module(adapter_module)
    records = adapter.load_records(str(resolved_path))
    print(f"Records loaded: {len(records)}")

    # Assign splits by external_item_id
    unique_items = sorted(set(r["external_item_id"] for r in records))
    item_splits = {}
    for i, item_id in enumerate(unique_items):
        item_splits[item_id] = SPLITS[i % len(SPLITS)]

    split_counts = {}
    for s in item_splits.values():
        split_counts[s] = split_counts.get(s, 0) + 1
    print(f"Items: {len(unique_items)}")
    print(f"Splits: {split_counts}")

    if args.dry_run:
        print("\nDry run — no database or S3 writes.")
        print(f"Would create dataset version: {dataset_version}")
        print(f"Would ingest {len(records)} images")
        # Validate a few images
        validated = 0
        for r in records[:5]:
            p = Path(r["source_file_path"])
            if p.exists():
                data = p.read_bytes()
                v = validate_image(data)
                status = "VALID" if v.get("valid") else f"INVALID: {v.get('issues')}"
                print(f"  {p.name}: {status}")
                validated += 1
        print(f"Sample validation: {validated} files checked")
        return

    # Connect
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    s3 = get_s3()
    now = datetime.now(UTC)

    # Check existing dataset
    cur.execute("SELECT id FROM reference_dataset_versions WHERE dataset_version = %s", (dataset_version,))
    existing = cur.fetchone()
    if existing:
        if not args.force:
            print(f"ERROR: Dataset '{dataset_version}' already exists. Use --force to replace.")
            sys.exit(1)
        # Clean up existing (only for safe prefixes)
        if not dataset_version.startswith(SAFE_PREFIXES):
            print(f"ERROR: Cannot auto-replace '{dataset_version}'. Only external_/synthetic_/smoke_ prefixes allowed.")
            sys.exit(1)
        ds_id = str(existing[0])
        cur.execute("DELETE FROM reference_embeddings WHERE reference_image_id IN (SELECT reference_image_id FROM reference_dataset_members WHERE dataset_version_id = %s)", (ds_id,))
        cur.execute("DELETE FROM reference_dataset_members WHERE dataset_version_id = %s", (ds_id,))
        cur.execute("DELETE FROM reference_dataset_versions WHERE id = %s", (ds_id,))
        print(f"Cleaned existing dataset: {dataset_version}")

    # Create dataset version
    ds_id = str(uuid.uuid4())
    cur.execute("""INSERT INTO reference_dataset_versions (id, dataset_version, description, source_type, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'draft', %s, %s)""",
                (ds_id, dataset_version, f"External dataset: {dataset_name}", "public_external", now, now))

    # Process records
    ingested = 0
    errors = 0
    item_ref_ids = {}  # external_item_id -> reference_item_id

    for record in records:
        ext_item = record["external_item_id"]

        # Create reference_item (once per external_item_id)
        if ext_item not in item_ref_ids:
            ref_item_id = str(uuid.uuid4())
            cur.execute("""INSERT INTO reference_items (id, authenticity_status, brand, category, material, source, label_confidence)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (ref_item_id, record["authenticity_status"], dataset_name, "external",
                         record["primary_label"], f"public_dataset:{dataset_name}", record["label_confidence"]))

            cur.execute("""INSERT INTO reference_label_reviews (id, reference_item_id, authenticity_status, label_confidence, provenance_type, notes)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (str(uuid.uuid4()), ref_item_id, record["authenticity_status"],
                         record["label_confidence"], record["provenance_type"],
                         f"External dataset {dataset_name}, item {ext_item}"))

            item_ref_ids[ext_item] = ref_item_id

        ref_item_id = item_ref_ids[ext_item]

        # Read and validate image
        source = Path(record["source_file_path"])
        if not source.exists():
            errors += 1
            continue

        try:
            raw_bytes = source.read_bytes()
            v = validate_image(raw_bytes)
            if not v.get("valid"):
                errors += 1
                continue
        except Exception:
            errors += 1
            continue

        # Upload raw to S3
        ext = source.suffix.lstrip(".")
        ref_image_id = str(uuid.uuid4())
        raw_key = f"external-datasets/{dataset_version}/raw/{ext_item}/{ref_image_id}.{ext}"
        s3.put_object(Bucket=S3_BUCKET, Key=raw_key, Body=raw_bytes)
        raw_uri = f"s3://{S3_BUCKET}/{raw_key}"

        # Create reference_image
        cur.execute("""INSERT INTO reference_images (id, reference_item_id, region_code, device_profile, lighting_profile, object_uri, quality_status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (ref_image_id, ref_item_id, record["region_code"], "EXTERNAL_DATASET",
                     "EXTERNAL_DATASET", raw_uri, "PASS"))

        # Normalize and embed
        try:
            norm_bytes = normalize_image(raw_bytes)
            embedding = compute_texture_embedding(norm_bytes, dim=EMBEDDING_DIM)
            vec_str = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"

            cur.execute("""INSERT INTO reference_embeddings (id, reference_image_id, embedding, embedding_model_version)
                           VALUES (%s, %s, %s::vector, %s)""",
                        (str(uuid.uuid4()), ref_image_id, vec_str, EMBEDDING_MODEL))
        except Exception as exc:
            print(f"  WARN: embedding failed for {source.name}: {exc}")

        # Dataset membership
        split = item_splits.get(ext_item, "train")
        in_search, in_eval, in_training = get_split_flags(split)
        cur.execute("""INSERT INTO reference_dataset_members (id, dataset_version_id, reference_image_id, split, include_in_search, include_in_evaluation, include_in_training)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), ds_id, ref_image_id, split, in_search, in_eval, in_training))

        ingested += 1

    # Audit
    cur.execute("""INSERT INTO audit_events (id, event_type, payload, created_at)
                   VALUES (%s, %s, %s, %s)""",
                (str(uuid.uuid4()),
                 "EXTERNAL_DATASET_INGESTED" if errors == 0 else "EXTERNAL_DATASET_INGESTED",
                 json.dumps({"dataset": dataset_version, "ingested": ingested, "errors": errors}),
                 now))

    print(f"\nIngested {ingested} images ({errors} errors)")
    print(f"Dataset: {dataset_version} (status=draft)")
    print("\nNext steps:")
    print(f"  make run-evaluation DATASET={dataset_version} MODEL=texture_baseline_v0.1.0")
    print("  make analyze-embeddings MODEL=texture_baseline_v0.1.0")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
