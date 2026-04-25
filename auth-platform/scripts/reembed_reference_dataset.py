#!/usr/bin/env python3
"""Re-embed reference images using a specified embedding model.

Usage:
  python scripts/reembed_reference_dataset.py --dataset synthetic_lv_monogram_v0.1.0 --model texture_baseline_v0.1.0 --dry-run
  python scripts/reembed_reference_dataset.py --dataset synthetic_lv_monogram_v0.1.0 --model learned_metric_v0.1.0 --force
"""

import argparse
import io
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import psycopg2
import torch

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))
sys.path.insert(0, str(Path(__file__).parent.parent / "libs" / "auth_common"))

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
S3_ENDPOINT = "http://localhost:4566"
EMBEDDING_DIM = 128


def get_s3():
    return boto3.client("s3", endpoint_url=S3_ENDPOINT,
                        aws_access_key_id="test", aws_secret_access_key="test",
                        region_name="us-east-1")


def embed_texture_baseline(img_bytes: bytes) -> list[float]:
    """Use texture_baseline_v0.1.0 embedding."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "imaging", str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py"))
    imaging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imaging)

    from auth_common.imaging import compute_texture_embedding, normalize_image
    norm = normalize_image(img_bytes)
    return compute_texture_embedding(norm, dim=EMBEDDING_DIM)


def embed_learned_metric(img_bytes: bytes, model: torch.nn.Module) -> list[float]:
    """Use learned_metric model for embedding."""
    from metric_learning.transforms import preprocess_for_inference

    tensor = preprocess_for_inference(img_bytes, input_size=224)
    model.eval()
    with torch.no_grad():
        embedding = model(tensor)
    return embedding.squeeze().tolist()


def load_learned_model(model_version: str, s3) -> torch.nn.Module:
    """Load model from S3."""
    from metric_learning.model import EmbeddingModel

    # Find artifact URI
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    cur.execute("SELECT artifact_uri FROM model_versions WHERE model_version = %s AND is_active = TRUE",
                (model_version,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise ValueError(f"No active model version: {model_version}")

    uri = row[0]
    parts = uri.replace("s3://", "").split("/", 1)
    response = s3.get_object(Bucket=parts[0], Key=parts[1])
    model_bytes = response["Body"].read()

    model = EmbeddingModel(embedding_dim=EMBEDDING_DIM)
    model.load_state_dict(torch.load(io.BytesIO(model_bytes), weights_only=True))
    model.eval()
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="e.g., learned_metric_v0.1.0 or texture_baseline_v0.1.0")
    parser.add_argument("--dataset", required=True, help="Dataset version to re-embed")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing")
    parser.add_argument("--force", action="store_true", help="Allow replacing existing embeddings for this dataset/model")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    s3 = get_s3()

    # Load model if learned
    learned_model = None
    if "learned_metric" in args.model:
        print(f"Loading model: {args.model}")
        learned_model = load_learned_model(args.model, s3)

    # Get search-eligible reference images
    cur.execute("""
        SELECT dm.reference_image_id, ri.object_uri, ri.region_code
        FROM reference_dataset_members dm
        JOIN reference_images ri ON ri.id = dm.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        WHERE rdv.dataset_version = %s AND dm.include_in_search = TRUE
        ORDER BY ri.id
    """, (args.dataset,))
    rows = cur.fetchall()
    print(f"Reference images to embed: {len(rows)}")

    # Also get evaluation-eligible images
    cur.execute("""
        SELECT dm.reference_image_id, ri.object_uri, ri.region_code
        FROM reference_dataset_members dm
        JOIN reference_images ri ON ri.id = dm.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        WHERE rdv.dataset_version = %s AND (dm.include_in_search = TRUE OR dm.include_in_evaluation = TRUE)
        ORDER BY ri.id
    """, (args.dataset,))
    all_rows = cur.fetchall()
    print(f"Total images (search + eval): {len(all_rows)}")
    if not all_rows:
        print(f"No reference images found for dataset: {args.dataset}")
        sys.exit(1)

    reference_image_ids = [str(row[0]) for row in all_rows]
    cur.execute(
        """
        SELECT count(*)
        FROM reference_embeddings
        WHERE embedding_model_version = %s AND reference_image_id = ANY(%s::uuid[])
        """,
        (args.model, reference_image_ids),
    )
    existing_count = cur.fetchone()[0]
    print("Replacement plan:")
    print(f"  dataset: {args.dataset}")
    print(f"  model:   {args.model}")
    print(f"  reference images to embed: {len(reference_image_ids)}")
    print(f"  existing embeddings to delete: {existing_count}")

    if args.dry_run:
        print("Dry run only. No embeddings deleted or inserted.")
        cur.close()
        conn.close()
        return

    if existing_count and not args.force:
        print("ERROR: Existing embeddings found. Re-run with --force to replace them.")
        sys.exit(1)

    if existing_count:
        cur.execute(
            """
            DELETE FROM reference_embeddings
            WHERE embedding_model_version = %s AND reference_image_id = ANY(%s::uuid[])
            """,
            (args.model, reference_image_ids),
        )
        print(f"Cleared {existing_count} old embeddings for {args.model} in {args.dataset}")

    embedded = 0
    for ref_image_id, object_uri, _region_code in all_rows:
        # Download image
        parts = object_uri.replace("s3://", "").split("/", 1)
        try:
            response = s3.get_object(Bucket=parts[0], Key=parts[1])
            img_bytes = response["Body"].read()
        except Exception as exc:
            print(f"  SKIP {ref_image_id}: {exc}")
            continue

        # Embed
        if learned_model:
            embedding = embed_learned_metric(img_bytes, learned_model)
        else:
            embedding = embed_texture_baseline(img_bytes)

        vec_str = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
        cur.execute("""
            INSERT INTO reference_embeddings (id, reference_image_id, embedding, embedding_model_version)
            VALUES (%s, %s, %s::vector, %s)
        """, (str(uuid.uuid4()), str(ref_image_id), vec_str, args.model))
        embedded += 1

    # Audit
    cur.execute("""
        INSERT INTO audit_events (id, event_type, payload, created_at)
        VALUES (%s, 'REFERENCE_REEMBEDDING_COMPLETED', %s, %s)
    """, (str(uuid.uuid4()),
          json.dumps({"model": args.model, "dataset": args.dataset, "count": embedded}),
          datetime.now(UTC)))

    print(f"\nEmbedded {embedded} reference images with {args.model}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
