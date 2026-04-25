#!/usr/bin/env python3
"""Ingest a validated capture batch: upload to S3, normalize, create reference records.

Usage: python scripts/ingest_capture_batch.py --batch lab_lv_monogram_batch_001
"""

import argparse
import importlib.util
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import psycopg2

_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)
normalize_image = _imaging.normalize_image

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
S3_ENDPOINT = "http://localhost:4566"
S3_BUCKET_RAW = "auth-platform-raw-evidence"
S3_BUCKET_NORM = "auth-platform-normalized-evidence"
S3_BUCKET_REF = "auth-platform-reference-library"


def get_s3():
    return boto3.client("s3", endpoint_url=S3_ENDPOINT, aws_access_key_id="test",
                        aws_secret_access_key="test", region_name="us-east-1")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    s3 = get_s3()
    now = datetime.now(UTC)

    # Check batch status
    cur.execute("SELECT id, status, batch_code FROM capture_batches WHERE batch_code = %s", (args.batch,))
    batch_row = cur.fetchone()
    if not batch_row:
        print(f"Batch not found: {args.batch}")
        sys.exit(1)

    batch_id, status, batch_code = batch_row
    if status not in ("VALIDATED", "VALIDATED_WITH_WARNINGS"):
        print(f"Batch status is '{status}', must be VALIDATED or VALIDATED_WITH_WARNINGS")
        sys.exit(1)

    # Get items
    cur.execute("SELECT id, external_item_id, brand, category, material, model, production_year, authenticity_status, label_confidence, provenance_type, notes FROM capture_batch_items WHERE capture_batch_id = %s", (str(batch_id),))
    items = cur.fetchall()

    ingested = 0
    for item_row in items:
        (item_id, ext_id, brand, category, material, model_name, prod_year,
         auth_status, label_conf, prov_type, notes) = item_row

        # Create reference_item
        ref_item_id = str(uuid.uuid4())
        cur.execute("""INSERT INTO reference_items (id, authenticity_status, brand, category, model, material, production_year, source, chain_of_custody, label_confidence)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (ref_item_id, auth_status, brand, category, model_name, material,
                     prod_year, f"capture_batch:{batch_code}", f"Batch {batch_code}, item {ext_id}", label_conf))

        # Create label review
        cur.execute("""INSERT INTO reference_label_reviews (id, reference_item_id, authenticity_status, label_confidence, provenance_type, notes)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), ref_item_id, auth_status, label_conf, prov_type,
                     notes or f"From batch {batch_code}"))

        # Get images for this item
        cur.execute("SELECT id, region_code, source_file_path, sha256_checksum, status FROM capture_batch_images WHERE capture_batch_item_id = %s AND status = 'VALIDATED'", (str(item_id),))
        images = cur.fetchall()

        for img_id, region_code, source_path, _sha256, _img_status in images:
            source = Path(source_path)
            if not source.exists():
                print(f"  SKIP: file missing {source}")
                continue

            raw_bytes = source.read_bytes()
            ext = source.suffix.lstrip(".")

            # Upload raw to S3
            raw_key = f"lab-captures/{batch_code}/items/{ext_id}/raw/{img_id}.{ext}"
            s3.put_object(Bucket=S3_BUCKET_REF, Key=raw_key, Body=raw_bytes)
            raw_uri = f"s3://{S3_BUCKET_REF}/{raw_key}"

            # Normalize
            try:
                norm_bytes = normalize_image(raw_bytes)
                norm_key = f"lab-captures/{batch_code}/items/{ext_id}/normalized/{img_id}_normalized.png"
                s3.put_object(Bucket=S3_BUCKET_REF, Key=norm_key, Body=norm_bytes, ContentType="image/png")
                norm_uri = f"s3://{S3_BUCKET_REF}/{norm_key}"
            except Exception as exc:
                print(f"  WARN: normalization failed for {source.name}: {exc}")
                norm_uri = None

            # Update batch image record
            cur.execute("UPDATE capture_batch_images SET raw_object_uri = %s, normalized_object_uri = %s, status = 'INGESTED' WHERE id = %s",
                        (raw_uri, norm_uri, str(img_id)))

            # Create reference_image
            ref_image_id = str(uuid.uuid4())
            cur.execute("""INSERT INTO reference_images (id, reference_item_id, region_code, device_profile, lighting_profile, object_uri, quality_status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (ref_image_id, ref_item_id, region_code, "LAB_CAPTURE", "LAB_DEFAULT", raw_uri, "PASS"))

            # Link batch image to reference image for promotion
            cur.execute("UPDATE capture_batch_images SET external_image_id = %s WHERE id = %s",
                        (ref_image_id, str(img_id)))

            ingested += 1

    # Update batch status
    cur.execute("UPDATE capture_batches SET status = 'INGESTED', updated_at = %s WHERE id = %s", (now, str(batch_id)))

    # Audit
    cur.execute("INSERT INTO audit_events (id, event_type, payload, created_at) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), "CAPTURE_BATCH_INGESTED",
                 json.dumps({"batch_code": batch_code, "images_ingested": ingested}), now))

    print(f"\nIngested {ingested} images from batch {batch_code}")
    print("Batch status: INGESTED")
    print("\nNext: make promote-capture-batch BATCH=... DATASET=...")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
