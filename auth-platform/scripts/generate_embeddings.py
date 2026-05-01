#!/usr/bin/env python3
"""Generate embeddings for a reference dataset under a chosen model version.

Targets the ``reference_embeddings`` table — the same destination used by
``reembed_reference_dataset.py``. Idempotent: images that already have an
embedding under (reference_image_id, embedding_model_version) are skipped.

Dispatches by ``embedding_model_version``:
  - texture_baseline_v0.1.0  -> auth_common.imaging.compute_texture_embedding
  - texture_baseline_v0.2.0  -> auth_common.imaging.compute_texture_embedding_v2
  - learned_metric_*         -> ml/metric_learning model (S3 artifact)
  - dinov2_base_frozen_*     -> services/embedding-service/app/embedders/dinov2_frozen

DELIBERATE ARCHITECTURAL CHOICE — DO NOT "FIX" BY ROUTING THROUGH HTTP.

This script imports the embedder modules directly rather than POSTing to the
embedding-service over HTTP. Reasoning:

  1. The HTTP path is keyed on ``image_asset_id`` and reads a normalized image
     URI from ``normalized_images``. Reference data is keyed on
     ``reference_image_id`` and lives in ``reference_images.object_uri``;
     there is no normalized_images row to look up.
  2. Reference-set ingestion is a batch / offline operation with different
     operational characteristics than live inference (no per-request auth,
     no rate limits, no SLO). Bypassing the service boundary is intentional
     for this code path.
  3. By importing the SAME embedder modules the service uses
     (``app.embedders.*`` + ``auth_common.imaging``), we keep reference
     embeddings on the same code path and same model versioning, which is
     what the governance story requires.

Tradeoff: any future middleware added to the embedding-service (auth, rate
limiting, telemetry) will NOT apply to reference data ingestion. That is the
correct behavior for batch reference work — if you need request-path
middleware to apply to reference embeddings later, build a dedicated batch
endpoint on the service rather than removing this direct-import path.

Usage:
  python scripts/generate_embeddings.py \
      --dataset external_leadata_v0.1.0 \
      --model dinov2_base_frozen_v0.1.0
  python scripts/generate_embeddings.py \
      --dataset external_fabricnet_v0.1.0 \
      --model dinov2_base_frozen_v0.1.0 --batch-size 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))
sys.path.insert(0, str(ROOT / "libs" / "auth_common"))
sys.path.insert(0, str(ROOT / "services" / "embedding-service"))

DB_DSN = os.environ.get(
    "AUTH_PLATFORM_DB_DSN",
    "postgresql://authplatform:authplatform@localhost:5432/authplatform",
)
S3_ENDPOINT = os.environ.get("AUTH_PLATFORM_S3_ENDPOINT", "http://localhost:4566")


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def fetch_dataset_images(cur, dataset_version: str) -> list[tuple]:
    cur.execute(
        """
        SELECT dm.reference_image_id, ri.object_uri, ri.region_code, dm.split
        FROM reference_dataset_members dm
        JOIN reference_images ri ON ri.id = dm.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        WHERE rdv.dataset_version = %s
          AND (dm.include_in_search = TRUE OR dm.include_in_evaluation = TRUE)
        ORDER BY ri.id
        """,
        (dataset_version,),
    )
    return cur.fetchall()


def fetch_existing_embedding_ids(cur, model_version: str, ref_image_ids: list[str]) -> set[str]:
    if not ref_image_ids:
        return set()
    cur.execute(
        """
        SELECT reference_image_id::text
        FROM reference_embeddings
        WHERE embedding_model_version = %s
          AND reference_image_id = ANY(%s::uuid[])
        """,
        (model_version, ref_image_ids),
    )
    return {row[0] for row in cur.fetchall()}


def load_image_bytes(s3, object_uri: str) -> bytes:
    parts = object_uri.replace("s3://", "").split("/", 1)
    response = s3.get_object(Bucket=parts[0], Key=parts[1])
    return response["Body"].read()


def normalize(img_bytes: bytes) -> bytes:
    from auth_common.imaging import normalize_image
    return normalize_image(img_bytes)


def select_embedder(model_version: str):
    """Return (callable, batch_capable) for the requested embedding model version."""
    if model_version.startswith("dinov2"):
        from app.embedders.dinov2_frozen import compute_dinov2_embeddings

        def batch_fn(norm_bytes_batch: list[bytes]) -> list[list[float]]:
            return compute_dinov2_embeddings(norm_bytes_batch)

        return batch_fn, True

    if "learned_metric" in model_version:
        import io as _io

        import torch
        from metric_learning.model import EmbeddingModel
        from metric_learning.transforms import preprocess_for_inference

        def _load() -> torch.nn.Module:
            conn = psycopg2.connect(DB_DSN)
            cur = conn.cursor()
            cur.execute(
                "SELECT artifact_uri FROM model_versions WHERE model_version = %s AND is_active = TRUE",
                (model_version,),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                raise ValueError(f"No active model_version row for {model_version}")
            uri = row[0]
            parts = uri.replace("s3://", "").split("/", 1)
            response = get_s3().get_object(Bucket=parts[0], Key=parts[1])
            model = EmbeddingModel(embedding_dim=128)
            model.load_state_dict(torch.load(_io.BytesIO(response["Body"].read()), weights_only=True, map_location="cpu"))
            model.eval()
            return model

        loaded = _load()

        def single_fn(norm_bytes_batch: list[bytes]) -> list[list[float]]:
            outs = []
            for nb in norm_bytes_batch:
                tensor = preprocess_for_inference(nb, input_size=224)
                with torch.no_grad():
                    embedding = loaded(tensor)
                outs.append(embedding.squeeze().tolist())
            return outs

        return single_fn, False

    if model_version == "texture_baseline_v0.2.0":
        from auth_common.imaging import compute_texture_embedding_v2

        def fn(norm_bytes_batch: list[bytes]) -> list[list[float]]:
            return [compute_texture_embedding_v2(nb, dim=256) for nb in norm_bytes_batch]

        return fn, False

    from auth_common.imaging import compute_texture_embedding

    def fn(norm_bytes_batch: list[bytes]) -> list[list[float]]:
        return [compute_texture_embedding(nb, dim=128) for nb in norm_bytes_batch]

    return fn, False


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="reference_dataset_version (e.g., external_leadata_v0.1.0)")
    parser.add_argument("--model", required=True, help="embedding_model_version (must exist in model_versions)")
    parser.add_argument("--batch-size", type=int, default=16, help="Inference batch size (DINOv2 only)")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N images (for smoke testing)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not write embeddings")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM model_versions WHERE model_version = %s AND is_active = TRUE",
        (args.model,),
    )
    if cur.fetchone() is None:
        print(f"ERROR: model_version {args.model} is not active in model_versions table.")
        return 2

    rows = fetch_dataset_images(cur, args.dataset)
    if not rows:
        print(f"No reference images found for dataset {args.dataset}.")
        return 1

    ref_image_ids = [str(r[0]) for r in rows]
    already = fetch_existing_embedding_ids(cur, args.model, ref_image_ids)
    pending = [r for r in rows if str(r[0]) not in already]
    if args.limit is not None:
        pending = pending[: args.limit]

    print(f"Dataset:           {args.dataset}")
    print(f"Model:             {args.model}")
    print(f"Reference images:  {len(rows)} total")
    print(f"Already embedded:  {len(already)}")
    print(f"To embed:          {len(pending)}")

    if args.dry_run or not pending:
        return 0

    embedder, batch_capable = select_embedder(args.model)
    s3 = get_s3()

    batch_size = max(1, args.batch_size if batch_capable else 1)
    embedded = 0
    failures = 0
    started = time.monotonic()

    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        norm_batch: list[bytes] = []
        valid_rows: list[tuple] = []
        for ref_image_id, object_uri, _region_code, _split in batch:
            try:
                raw = load_image_bytes(s3, object_uri)
                norm_batch.append(normalize(raw))
                valid_rows.append((ref_image_id, object_uri))
            except Exception as exc:
                failures += 1
                print(f"  SKIP {ref_image_id}: {exc}")

        if not norm_batch:
            continue

        try:
            embeddings = embedder(norm_batch)
        except Exception as exc:
            failures += len(norm_batch)
            print(f"  EMBED_FAIL batch starting at {valid_rows[0][0]}: {exc}")
            continue

        for (ref_image_id, _object_uri), emb in zip(valid_rows, embeddings, strict=True):
            cur.execute(
                """
                INSERT INTO reference_embeddings (id, reference_image_id, embedding, embedding_model_version)
                VALUES (%s, %s, %s::vector, %s)
                """,
                (str(uuid.uuid4()), str(ref_image_id), vector_literal(emb), args.model),
            )
            embedded += 1

        elapsed = time.monotonic() - started
        rate = embedded / elapsed if elapsed > 0 else 0.0
        print(f"  progress: embedded={embedded} failures={failures} rate={rate:.1f}/s")

    cur.execute(
        """
        INSERT INTO audit_events (id, event_type, payload, created_at)
        VALUES (%s, 'REFERENCE_EMBEDDINGS_GENERATED', %s, %s)
        """,
        (
            str(uuid.uuid4()),
            json.dumps(
                {
                    "model": args.model,
                    "dataset": args.dataset,
                    "embedded": embedded,
                    "failures": failures,
                    "skipped_existing": len(already),
                }
            ),
            datetime.now(UTC),
        ),
    )

    print(f"\nEmbedded {embedded} reference images with {args.model} (failures: {failures})")
    cur.close()
    conn.close()
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
