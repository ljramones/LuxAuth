"""Audit event helper for recording platform actions."""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.logging import get_logger

logger = get_logger("audit")


async def record_audit_event(
    db: AsyncSession,
    event_type: str,
    *,
    correlation_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    scan_session_id: uuid.UUID | None = None,
    image_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> None:
    """Insert a row into the audit_events table."""
    await db.execute(
        text(
            """
            INSERT INTO audit_events
                (id, event_type, correlation_id, tenant_id, scan_session_id,
                 image_id, actor_id, payload, created_at)
            VALUES
                (:id, :event_type, :correlation_id, :tenant_id, :scan_session_id,
                 :image_id, :actor_id, :payload, :created_at)
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "correlation_id": str(correlation_id) if correlation_id else None,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "scan_session_id": str(scan_session_id) if scan_session_id else None,
            "image_id": str(image_id) if image_id else None,
            "actor_id": str(actor_id) if actor_id else None,
            "payload": json.dumps(payload) if payload else None,
            "created_at": datetime.now(UTC),
        },
    )
    logger.info("audit_event_recorded", event_type=event_type, scan_session_id=str(scan_session_id) if scan_session_id else None)
