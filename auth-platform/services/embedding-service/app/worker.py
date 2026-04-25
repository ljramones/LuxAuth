"""SQS worker handler for embedding generation."""

from uuid import UUID

from auth_common.database import get_engine, get_session_factory
from auth_common.events import EventEnvelope
from auth_common.idempotency import (
    check_idempotency,
    make_idempotency_key,
    record_processing_complete,
    record_processing_failed,
    record_processing_start,
)
from auth_common.logging import get_logger

from app.handlers import generate_embedding
from app.settings import settings

logger = get_logger(settings.service_name)

EMBEDDING_MODEL_VERSION = "stub_embedder_v0.1.0"

_engine = None
_factory = None


def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = get_engine(settings.database_url)
        _factory = get_session_factory(_engine)
    return _factory


async def handle_message(envelope: EventEnvelope) -> None:
    """Process an IMAGE_NORMALIZED event from the queue."""
    image_id_str = (
        str(envelope.image_id)
        if envelope.image_id
        else envelope.payload.get("image_asset_id")
    )
    if not image_id_str:
        logger.warning("missing_image_id", event_id=str(envelope.event_id))
        return

    image_id = UUID(image_id_str)
    idem_key = make_idempotency_key(str(image_id), "EMBEDDING", EMBEDDING_MODEL_VERSION)

    factory = _get_factory()
    async with factory() as db:
        if await check_idempotency(db, idem_key):
            await db.commit()
            return

        await record_processing_start(
            db, idem_key, "EMBEDDING",
            image_id=image_id,
            scan_session_id=envelope.scan_session_id,
        )
        await db.commit()

    async with factory() as db:
        try:
            await generate_embedding(image_id, db)
            await record_processing_complete(db, idem_key)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            async with factory() as err_db:
                await record_processing_failed(err_db, idem_key, str(exc))
                await err_db.commit()
            raise
