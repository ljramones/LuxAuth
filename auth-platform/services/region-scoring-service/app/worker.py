"""SQS worker handler for region scoring."""

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

from app.handlers import score_region
from app.settings import settings

logger = get_logger(settings.service_name)

SCORING_RULE_VERSION = "scoring_rules_v0.1.0"

_engine = None
_factory = None


def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = get_engine(settings.database_url)
        _factory = get_session_factory(_engine)
    return _factory


async def handle_message(envelope: EventEnvelope) -> None:
    """Process a VECTOR_SEARCH_COMPLETED event."""
    payload = envelope.payload
    image_id_str = str(envelope.image_id) if envelope.image_id else payload.get("image_asset_id")
    scan_session_id = str(envelope.scan_session_id) if envelope.scan_session_id else payload.get("scan_session_id")
    region_code = envelope.region_code or payload.get("region_code")

    if not image_id_str or not scan_session_id:
        logger.warning("missing_required_fields", event_id=str(envelope.event_id))
        return

    image_id = UUID(image_id_str)
    idem_key = make_idempotency_key(str(image_id), "REGION_SCORING", SCORING_RULE_VERSION)

    authentic_sim = payload.get("authentic_cluster_score", 0.85)
    counterfeit_sim = payload.get("counterfeit_cluster_score", 0.35)
    ood = payload.get("ood_score", 0.15)

    factory = _get_factory()
    async with factory() as db:
        if await check_idempotency(db, idem_key):
            await db.commit()
            return
        await record_processing_start(db, idem_key, "REGION_SCORING", image_id=image_id)
        await db.commit()

    async with factory() as db:
        try:
            # Look up region_code from image_assets if not in envelope
            if not region_code:
                from sqlalchemy import text
                row = await db.execute(
                    text("SELECT region_code FROM image_assets WHERE id = :id"),
                    {"id": str(image_id)},
                )
                region_code = row.scalar_one_or_none() or "UNKNOWN"

            await score_region(
                image_asset_id=str(image_id),
                scan_session_id=scan_session_id,
                region_code=region_code,
                authentic_similarity=authentic_sim,
                counterfeit_similarity=counterfeit_sim,
                ood_score=ood,
                db_session=db,
            )
            await record_processing_complete(db, idem_key)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            async with factory() as err_db:
                await record_processing_failed(err_db, idem_key, str(exc))
                await err_db.commit()
            raise
