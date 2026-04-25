from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.events import EventEnvelope, EventTypes
from auth_common.imaging import compute_texture_embedding
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import EmbeddingRecord
from auth_common.s3 import download_file

from app.settings import settings

logger = get_logger(settings.service_name)

EMBEDDING_DIM = 128
EMBEDDING_MODEL_VERSION = "texture_baseline_v0.1.0"


async def generate_embedding(
    image_asset_id: UUID, db_session: AsyncSession
) -> EmbeddingRecord:
    """Generate texture baseline embedding from normalized image."""

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

    # Compute real texture embedding
    embedding = compute_texture_embedding(norm_bytes, dim=EMBEDDING_DIM)

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
            "model_version": EMBEDDING_MODEL_VERSION,
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
        payload={"embedding_model_version": EMBEDDING_MODEL_VERSION, "dim": EMBEDDING_DIM},
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
            "embedding_model_version": EMBEDDING_MODEL_VERSION,
        },
    )
    send_message(settings.sqs_vector_search_queue, envelope)
    logger.info("embedding_generated", image_asset_id=str(image_asset_id))

    return EmbeddingRecord(
        image_asset_id=image_asset_id,
        embedding=embedding[:10],
        embedding_model_version=EMBEDDING_MODEL_VERSION,
    )
