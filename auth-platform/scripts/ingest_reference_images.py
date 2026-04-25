#!/usr/bin/env python3
"""Ingest reference images from sample_data/reference/ into the platform.

For each image:
1. Find or create reference_item
2. Create reference_image record
3. Upload raw image to S3
4. Normalize the image
5. Generate texture_baseline_v0.1.0 embedding
6. Store embedding in reference_embeddings table
7. Create reference_dataset_members row linking to dataset version
8. Create reference_label_reviews row

Usage:
  python scripts/ingest_reference_images.py --dataset synthetic_lv_monogram_v0.1.0 --dry-run
  python scripts/ingest_reference_images.py --dataset synthetic_lv_monogram_v0.1.0 --force
"""

import argparse
import importlib.util
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import psycopg2

# Import imaging module directly to avoid loading full auth_common package
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
SAFE_DESTRUCTIVE_PREFIXES = ("synthetic_", "smoke_")

# Deterministic split assignment: cycle through for indices 0-4
SPLITS = ["train", "train", "train", "validation", "test"]


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def get_split_flags(split):
    """Return (include_in_search, include_in_evaluation, include_in_training) for a split."""
    if split == "train":
        return True, False, True
    elif split == "validation" or split == "test":
        return False, True, False
    else:
        raise ValueError(f"Unknown split: {split}")


def _fetch_existing_dataset(cur, dataset_version: str) -> tuple[str | None, dict[str, int], list[str], list[str]]:
    cur.execute("SELECT id FROM reference_dataset_versions WHERE dataset_version = %s", (dataset_version,))
    row = cur.fetchone()
    if not row:
        return None, {
            "reference_label_reviews": 0,
            "reference_dataset_members": 0,
            "reference_embeddings": 0,
            "reference_images": 0,
            "reference_items": 0,
            "reference_dataset_versions": 0,
        }, [], []

    dataset_id = str(row[0])
    cur.execute(
        """
        SELECT DISTINCT ri.id, ri.reference_item_id
        FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        WHERE rdm.dataset_version_id = %s
        """,
        (dataset_id,),
    )
    rows = cur.fetchall()
    reference_image_ids = [str(r[0]) for r in rows]
    reference_item_ids = sorted({str(r[1]) for r in rows})

    counts = {"reference_dataset_versions": 1}
    counts["reference_dataset_members"] = len(reference_image_ids)
    if reference_image_ids:
        cur.execute("SELECT count(*) FROM reference_embeddings WHERE reference_image_id = ANY(%s)", (reference_image_ids,))
        counts["reference_embeddings"] = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM reference_label_reviews WHERE reference_image_id = ANY(%s)", (reference_image_ids,))
        image_review_count = cur.fetchone()[0]
    else:
        counts["reference_embeddings"] = 0
        image_review_count = 0

    if reference_item_ids:
        cur.execute("SELECT count(*) FROM reference_label_reviews WHERE reference_item_id = ANY(%s)", (reference_item_ids,))
        item_review_count = cur.fetchone()[0]
    else:
        item_review_count = 0
    counts["reference_label_reviews"] = image_review_count + item_review_count
    counts["reference_images"] = len(reference_image_ids)
    counts["reference_items"] = len(reference_item_ids)
    return dataset_id, counts, reference_image_ids, reference_item_ids


def _print_delete_plan(dataset_version: str, counts: dict[str, int]) -> None:
    print(f"Delete plan for dataset '{dataset_version}':")
    for table in (
        "reference_label_reviews",
        "reference_dataset_members",
        "reference_embeddings",
        "reference_images",
        "reference_items",
        "reference_dataset_versions",
    ):
        print(f"  {table}: {counts.get(table, 0)} rows")


def _delete_existing_dataset(cur, dataset_id: str, reference_image_ids: list[str], reference_item_ids: list[str]) -> None:
    if reference_image_ids:
        cur.execute("DELETE FROM reference_label_reviews WHERE reference_image_id = ANY(%s)", (reference_image_ids,))
        cur.execute("DELETE FROM reference_embeddings WHERE reference_image_id = ANY(%s)", (reference_image_ids,))
    if reference_item_ids:
        cur.execute("DELETE FROM reference_label_reviews WHERE reference_item_id = ANY(%s)", (reference_item_ids,))
    cur.execute("DELETE FROM reference_dataset_members WHERE dataset_version_id = %s", (dataset_id,))
    if reference_image_ids:
        cur.execute("DELETE FROM reference_images WHERE id = ANY(%s)", (reference_image_ids,))
    if reference_item_ids:
        cur.execute("DELETE FROM reference_items WHERE id = ANY(%s)", (reference_item_ids,))
    cur.execute("DELETE FROM reference_dataset_versions WHERE id = %s", (dataset_id,))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Dataset version to create, e.g. synthetic_lv_monogram_v0.1.0")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing")
    parser.add_argument("--force", action="store_true", help="Allow replacement when the dataset already exists")
    parser.add_argument("--force-real-data", action="store_true", help="Allow destructive replacement of non-smoke/non-synthetic datasets")
    args = parser.parse_args()

    if not REFERENCE_DIR.exists():
        print(f"Reference directory not found: {REFERENCE_DIR}")
        print("Run: python scripts/generate_synthetic_reference_images.py first")
        sys.exit(1)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    s3 = get_s3()

    dataset_id, delete_counts, reference_image_ids, reference_item_ids = _fetch_existing_dataset(cur, args.dataset)
    if dataset_id:
        _print_delete_plan(args.dataset, delete_counts)
        if not args.force:
            print("ERROR: Dataset already exists. Re-run with --force to replace it.")
            sys.exit(1)
        if not args.dataset.startswith(SAFE_DESTRUCTIVE_PREFIXES) and not args.force_real_data:
            print("ERROR: Refusing destructive cleanup for non-smoke/non-synthetic dataset without --force-real-data.")
            sys.exit(1)
    else:
        print(f"No existing dataset found for '{args.dataset}'.")

    if args.dry_run:
        print("Dry run only. No rows deleted or inserted.")
        cur.close()
        conn.close()
        return

    if dataset_id:
        _delete_existing_dataset(cur, dataset_id, reference_image_ids, reference_item_ids)

    # Create dataset version
    ds_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    cur.execute(
        """INSERT INTO reference_dataset_versions
           (id, dataset_version, source_type, status, created_at)
           VALUES (%s, %s, %s, %s, %s)""",
        (ds_id, args.dataset, "synthetic", "active", now),
    )
    print(f"Created dataset version: {args.dataset} ({ds_id})")

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

                    # Create label review for this item
                    cur.execute(
                        """INSERT INTO reference_label_reviews
                           (id, reference_item_id, authenticity_status, label_confidence,
                            provenance_type, notes)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (str(uuid.uuid4()), item_id, authenticity, "high",
                         "synthetic", "Synthetic local-dev sample, not real authentication data"),
                    )

                    for region_dir in sorted(mat_dir.iterdir()):
                        if not region_dir.is_dir():
                            continue
                        region_code = region_dir.name

                        for img_path in sorted(region_dir.glob("*.jpg")):
                            raw_bytes = img_path.read_bytes()
                            ref_image_id = str(uuid.uuid4())

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

                            # Determine split
                            split = SPLITS[ingested % len(SPLITS)]
                            in_search, in_eval, in_train = get_split_flags(split)

                            # Create dataset member
                            cur.execute(
                                """INSERT INTO reference_dataset_members
                                   (id, dataset_version_id, reference_image_id, split,
                                    include_in_search, include_in_evaluation, include_in_training)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (str(uuid.uuid4()), ds_id, ref_image_id, split,
                                 in_search, in_eval, in_train),
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

    # Print split summary
    cur.execute(
        """SELECT split, count(*) FROM reference_dataset_members
           WHERE dataset_version_id = %s GROUP BY split ORDER BY split""",
        (ds_id,),
    )
    print("\nSplit distribution:")
    for split, count in cur.fetchall():
        print(f"  {split}: {count}")

    cur.close()
    conn.close()
    print(f"\nIngested {ingested} reference images with embeddings.")
    print("NOTE: This is synthetic test data, not real authentication data.")


if __name__ == "__main__":
    main()
