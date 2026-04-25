"""Idempotency protection for pipeline processing stages."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.logging import get_logger

logger = get_logger("idempotency")


def make_idempotency_key(*parts: str) -> str:
    """Build an idempotency key from component parts."""
    return "|".join(str(p) for p in parts)


async def check_idempotency(
    db: AsyncSession,
    idempotency_key: str,
) -> bool:
    """Return True if this key has already been completed (should skip)."""
    result = await db.execute(
        text(
            "SELECT status FROM processing_runs WHERE idempotency_key = :key"
        ),
        {"key": idempotency_key},
    )
    row = result.mappings().first()
    if row and row["status"] == "COMPLETED":
        logger.info("idempotency_skip", idempotency_key=idempotency_key)
        return True
    return False


async def record_processing_start(
    db: AsyncSession,
    idempotency_key: str,
    stage: str,
    *,
    scan_session_id: uuid.UUID | None = None,
    image_id: uuid.UUID | None = None,
) -> str:
    """Record that processing has started. Returns the run ID."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            """
            INSERT INTO processing_runs
                (id, idempotency_key, stage, scan_session_id, image_id,
                 status, started_at, created_at, updated_at)
            VALUES
                (:id, :key, :stage, :ssid, :iid,
                 'STARTED', :now, :now, :now)
            ON CONFLICT (idempotency_key) DO NOTHING
            """
        ),
        {
            "id": run_id,
            "key": idempotency_key,
            "stage": stage,
            "ssid": str(scan_session_id) if scan_session_id else None,
            "iid": str(image_id) if image_id else None,
            "now": now,
        },
    )
    return run_id


async def record_processing_complete(
    db: AsyncSession,
    idempotency_key: str,
) -> None:
    """Mark a processing run as completed."""
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            """
            UPDATE processing_runs
            SET status = 'COMPLETED', completed_at = :now, updated_at = :now
            WHERE idempotency_key = :key
            """
        ),
        {"key": idempotency_key, "now": now},
    )


async def record_processing_failed(
    db: AsyncSession,
    idempotency_key: str,
    error_message: str,
) -> None:
    """Mark a processing run as failed."""
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            """
            UPDATE processing_runs
            SET status = 'FAILED', error_message = :err, completed_at = :now, updated_at = :now
            WHERE idempotency_key = :key
            """
        ),
        {"key": idempotency_key, "err": error_message, "now": now},
    )
