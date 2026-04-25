import hashlib
import math
import random
import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import EmbeddingRecord

from app.settings import settings

logger = get_logger(settings.service_name)

EMBEDDING_DIM = 768
EMBEDDING_MODEL_VERSION = "stub_embedder_v0.1.0"


def _generate_embedding(image_asset_id: UUID) -> list[float]:
    """Generate a deterministic fake 768-dim unit-length embedding."""
    seed = int(
        hashlib.sha256(str(image_asset_id).encode()).hexdigest(), 16
    ) % (2**32)
    rng = random.Random(seed)
    raw = [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]
    magnitude = math.sqrt(sum(x * x for x in raw))
    return [x / magnitude for x in raw]


async def generate_embedding(
    image_asset_id: UUID, db_session: AsyncSession
) -> EmbeddingRecord:
    """Generate and store a vector embedding for the given image asset."""

    embedding = _generate_embedding(image_asset_id)

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

    # Look up scan_session_id for the event payload
    row = await db_session.execute(
        text("SELECT scan_session_id FROM image_assets WHERE id = :id"),
        {"id": str(image_asset_id)},
    )
    scan_session_id = row.scalar_one_or_none()

    # Publish downstream event
    envelope = EventEnvelope(
        event_type=EventTypes.EMBEDDING_GENERATED,
        payload={
            "image_asset_id": str(image_asset_id),
            "scan_session_id": str(scan_session_id) if scan_session_id else None,
            "embedding_model_version": EMBEDDING_MODEL_VERSION,
        },
    )
    send_message(settings.sqs_vector_search_queue, envelope)
    logger.info(
        "embedding generated - published to vector-search queue",
        extra={"image_asset_id": str(image_asset_id)},
    )

    # TODO: emit audit event

    return EmbeddingRecord(
        image_asset_id=image_asset_id,
        embedding=embedding[:10],  # Only first 10 elements for brevity
        embedding_model_version=EMBEDDING_MODEL_VERSION,
    )
