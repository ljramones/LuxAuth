import io
from uuid import UUID

try:
    import torch
except ImportError:
    torch = None  # type: ignore

from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.events import EventEnvelope, EventTypes
from auth_common.imaging import compute_texture_embedding, compute_texture_embedding_v2
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import EmbeddingRecord
from auth_common.s3 import download_file
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings

logger = get_logger(settings.service_name)

EMBEDDING_DIM = 128
_learned_model = None


def _get_learned_model():
    """Lazy-load the learned metric model from S3."""
    global _learned_model
    if _learned_model is not None:
        return _learned_model

    try:
        # Import model class
        import sys
        sys.path.insert(0, "/app/ml")
        # Find artifact in DB — use sync psycopg2 for simplicity
        import psycopg2
        from metric_learning.model import EmbeddingModel
        conn = psycopg2.connect(
            f"postgresql://authplatform:authplatform@{settings.database_url.split('@')[1].split('/')[0]}/authplatform"
        )
        cur = conn.cursor()
        cur.execute("SELECT artifact_uri FROM model_versions WHERE model_version = %s AND is_active = TRUE",
                    (settings.embedding_model_version,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            raise ValueError(f"No active model: {settings.embedding_model_version}")

        uri = row[0]
        parts = uri.replace("s3://", "").split("/", 1)
        model_bytes = download_file(parts[0], parts[1])

        model = EmbeddingModel(embedding_dim=EMBEDDING_DIM)
        model.load_state_dict(torch.load(io.BytesIO(model_bytes), weights_only=True, map_location="cpu"))
        model.eval()
        _learned_model = model
        logger.info("learned_model_loaded", version=settings.embedding_model_version)
        return model
    except Exception as exc:
        logger.error("learned_model_load_failed", error=str(exc))
        raise


def _embed_texture_baseline(norm_bytes: bytes) -> list[float]:
    return compute_texture_embedding(norm_bytes, dim=128)


def _embed_texture_baseline_v2(norm_bytes: bytes) -> list[float]:
    return compute_texture_embedding_v2(norm_bytes, dim=256)


def _embed_learned_metric(norm_bytes: bytes) -> list[float]:
    try:
        import sys
        sys.path.insert(0, "/app/ml")
        from metric_learning.transforms import preprocess_for_inference
        model = _get_learned_model()
        tensor = preprocess_for_inference(norm_bytes, input_size=224)
        with torch.no_grad():
            embedding = model(tensor)
        return embedding.squeeze().tolist()
    except ImportError:
        logger.warning("torch_not_available_falling_back_to_baseline")
        return _embed_texture_baseline(norm_bytes)


async def generate_embedding(
    image_asset_id: UUID, db_session: AsyncSession
) -> EmbeddingRecord:
    """Generate embedding using the configured backend."""

    model_version = settings.embedding_model_version

    # Look up normalized image URI
    row = await db_session.execute(
        text("SELECT normalized_object_uri FROM normalized_images WHERE image_asset_id = :id"),
        {"id": str(image_asset_id)},
    )
    norm_row = row.mappings().one_or_none()
    if norm_row is None:
        raise ValueError(f"No normalized image for {image_asset_id}")

    norm_uri = norm_row["normalized_object_uri"]
    uri_parts = norm_uri.replace("s3://", "").split("/", 1)
    norm_bytes = download_file(uri_parts[0], uri_parts[1])

    # Select backend
    if "learned_metric" in model_version:
        embedding = _embed_learned_metric(norm_bytes)
    elif model_version == "texture_baseline_v0.2.0":
        embedding = _embed_texture_baseline_v2(norm_bytes)
    else:
        embedding = _embed_texture_baseline(norm_bytes)

    # Format as pgvector literal
    vec_str = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"

    # Store in embeddings table
    await db_session.execute(
        text(
            """
            INSERT INTO embeddings
                (image_asset_id, embedding, embedding_model_version)
            VALUES
                (:image_asset_id, cast(:embedding as vector), :model_version)
            ON CONFLICT (image_asset_id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                embedding_model_version = EXCLUDED.embedding_model_version
            """
        ),
        {
            "image_asset_id": str(image_asset_id),
            "embedding": vec_str,
            "model_version": model_version,
        },
    )
    await db_session.commit()

    # Look up scan_session_id
    row2 = await db_session.execute(
        text("SELECT scan_session_id FROM image_assets WHERE id = :id"),
        {"id": str(image_asset_id)},
    )
    scan_session_id = row2.scalar_one_or_none()

    await record_audit_event(
        db_session,
        "EMBEDDING_GENERATED",
        image_id=image_asset_id,
        scan_session_id=scan_session_id,
        payload={"embedding_model_version": model_version, "dim": EMBEDDING_DIM},
    )

    envelope = EventEnvelope(
        event_type=EventTypes.EMBEDDING_GENERATED,
        correlation_id=get_correlation_id(),
        scan_session_id=scan_session_id,
        image_id=image_asset_id,
        source_service=settings.service_name,
        payload={
            "image_asset_id": str(image_asset_id),
            "scan_session_id": str(scan_session_id) if scan_session_id else None,
            "embedding_model_version": model_version,
        },
    )
    send_message(settings.sqs_vector_search_queue, envelope)
    logger.info("embedding_generated", image_asset_id=str(image_asset_id), model=model_version)

    return EmbeddingRecord(
        image_asset_id=image_asset_id,
        embedding=embedding[:10],
        embedding_model_version=model_version,
    )
