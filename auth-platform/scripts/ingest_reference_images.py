#!/usr/bin/env python3
"""Ingest reference images from sample_data/reference/ into the platform.

For each image:
1. Find or create reference_item
2. Create reference_image record
3. Upload raw image to S3
4. Normalize the image
5. Generate texture_baseline_v0.1.0 embedding
6. Store embedding in reference_embeddings table

Usage: python scripts/ingest_reference_images.py
"""

import hashlib
import sys
import uuid
from pathlib import Path

import psycopg2
import boto3

# Import imaging module directly to avoid loading full auth_common package
import importlib.util
_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)
normalize_image = _imaging.normalize_image
compute_texture_embedding = _imaging.compute_texture_embedding

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
S3_ENDPOINT = "http://localhost:4566"
S3_BUCKET_RAW = "auth-platform-reference-library"
EMBEDDING_MODEL = "texture_baseline_v0.1.0"
EMBEDDING_DIM = 128

REFERENCE_DIR = Path("sample_data/reference")


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def main():
    if not REFERENCE_DIR.exists():
        print(f"Reference directory not found: {REFERENCE_DIR}")
        print("Run: python scripts/generate_synthetic_reference_images.py first")
        sys.exit(1)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    s3 = get_s3()

    # Clear existing reference data for clean re-ingestion
    cur.execute("DELETE FROM reference_embeddings")
    cur.execute("DELETE FROM reference_images")
    cur.execute("DELETE FROM reference_items WHERE source = 'synthetic_test_data'")

    ingested = 0

    for auth_status_dir in sorted(REFERENCE_DIR.iterdir()):
        if not auth_status_dir.is_dir():
            continue

        authenticity = (
            "CONFIRMED_AUTHENTIC" if auth_status_dir.name == "authentic"
            else "CONFIRMED_COUNTERFEIT"
        )

        for brand_dir in sorted(auth_status_dir.iterdir()):
            if not brand_dir.is_dir():
                continue
            brand = brand_dir.name.replace("_", " ")

            for cat_dir in sorted(brand_dir.iterdir()):
                if not cat_dir.is_dir():
                    continue
                category = cat_dir.name

                for mat_dir in sorted(cat_dir.iterdir()):
                    if not mat_dir.is_dir():
                        continue
                    material = mat_dir.name

                    # Create reference_item for this group
                    item_id = str(uuid.uuid4())
                    cur.execute(
                        """INSERT INTO reference_items
                           (id, authenticity_status, brand, category, material, source, label_confidence)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (item_id, authenticity, brand, category, material, "synthetic_test_data", "TEST"),
                    )

                    for region_dir in sorted(mat_dir.iterdir()):
                        if not region_dir.is_dir():
                            continue
                        region_code = region_dir.name

                        for img_path in sorted(region_dir.glob("*.jpg")):
                            raw_bytes = img_path.read_bytes()
                            ref_image_id = str(uuid.uuid4())
                            sha256 = hashlib.sha256(raw_bytes).hexdigest()

                            # Upload to S3
                            s3_key = f"reference/{brand}/{category}/{material}/{region_code}/{ref_image_id}.jpg"
                            s3.put_object(
                                Bucket=S3_BUCKET_RAW,
                                Key=s3_key,
                                Body=raw_bytes,
                                ContentType="image/jpeg",
                            )
                            object_uri = f"s3://{S3_BUCKET_RAW}/{s3_key}"

                            # Create reference_image
                            cur.execute(
                                """INSERT INTO reference_images
                                   (id, reference_item_id, region_code, device_profile,
                                    lighting_profile, object_uri, quality_status)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (ref_image_id, item_id, region_code, "SYNTHETIC",
                                 "SYNTHETIC", object_uri, "PASS"),
                            )

                            # Normalize + embed
                            try:
                                norm_bytes = normalize_image(raw_bytes)
                                embedding = compute_texture_embedding(norm_bytes, dim=EMBEDDING_DIM)
                                vec_str = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"

                                cur.execute(
                                    """INSERT INTO reference_embeddings
                                       (id, reference_image_id, embedding, embedding_model_version)
                                       VALUES (%s, %s, %s::vector, %s)""",
                                    (str(uuid.uuid4()), ref_image_id, vec_str, EMBEDDING_MODEL),
                                )
                            except Exception as exc:
                                print(f"    WARNING: embedding failed for {img_path.name}: {exc}")

                            ingested += 1

    cur.close()
    conn.close()
    print(f"\nIngested {ingested} reference images with embeddings.")
    print("NOTE: This is synthetic test data, not real authentication data.")


if __name__ == "__main__":
    main()
