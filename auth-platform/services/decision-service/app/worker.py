"""SQS worker handler for decision service."""

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
from sqlalchemy import text

from app.handlers import DECISION_RULE_VERSION, make_decision
from app.settings import settings

logger = get_logger(settings.service_name)

_engine = None
_factory = None


def _get_factory():
    global _engine, _factory
    if _factory is None:
        _engine = get_engine(settings.database_url)
        _factory = get_session_factory(_engine)
    return _factory


async def handle_message(envelope: EventEnvelope) -> None:
    """Process a REGION_SCORED event. Check if all regions are scored, then decide."""
    scan_session_id = (
        str(envelope.scan_session_id)
        if envelope.scan_session_id
        else envelope.payload.get("scan_session_id")
    )
    if not scan_session_id:
        logger.warning("missing_scan_session_id", event_id=str(envelope.event_id))
        return

    factory = _get_factory()

    # Check if decision already exists for this scan session
    async with factory() as db:
        existing = await db.execute(
            text("SELECT id FROM authentication_decisions WHERE scan_session_id = :sid"),
            {"sid": scan_session_id},
        )
        if existing.first():
            logger.info("decision_already_exists", scan_session_id=scan_session_id)
            return

    # Check if all required regions are scored
    async with factory() as db:
        # Get required regions
        session_row = await db.execute(
            text("SELECT scan_recipe_id FROM scan_sessions WHERE id = :sid"),
            {"sid": scan_session_id},
        )
        session = session_row.mappings().first()
        if not session or not session["scan_recipe_id"]:
            logger.warning("no_recipe_for_session", scan_session_id=scan_session_id)
            return

        required = await db.execute(
            text("SELECT region_code FROM scan_recipe_regions WHERE scan_recipe_id = :rid"),
            {"rid": str(session["scan_recipe_id"])},
        )
        required_regions = {r["region_code"] for r in required.mappings()}

        scored = await db.execute(
            text("SELECT DISTINCT region_code FROM region_scores WHERE scan_session_id = :sid"),
            {"sid": scan_session_id},
        )
        scored_regions = {r["region_code"] for r in scored.mappings()}

        if not required_regions.issubset(scored_regions):
            logger.info(
                "waiting_for_regions",
                scan_session_id=scan_session_id,
                missing=list(required_regions - scored_regions),
            )
            return

    # All regions scored — make decision
    idem_key = make_idempotency_key(scan_session_id, "DECISION", DECISION_RULE_VERSION)

    async with factory() as db:
        if await check_idempotency(db, idem_key):
            await db.commit()
            return
        await record_processing_start(db, idem_key, "DECISION", scan_session_id=UUID(scan_session_id))
        await db.commit()

    async with factory() as db:
        try:
            await make_decision(scan_session_id, db)
            await record_processing_complete(db, idem_key)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            async with factory() as err_db:
                await record_processing_failed(
                    err_db,
                    idem_key,
                    str(exc),
                    correlation_id=envelope.correlation_id,
                    scan_session_id=scan_session_id,
                    stage="DECISION",
                    source_service=settings.service_name,
                    event_id=envelope.event_id,
                )
                await err_db.commit()
            raise
