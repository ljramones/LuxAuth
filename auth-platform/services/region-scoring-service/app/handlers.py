import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import RegionScore

from app.settings import settings

logger = get_logger(settings.service_name)


async def score_region(
    image_asset_id: str,
    scan_session_id: str,
    region_code: str,
    authentic_similarity: float,
    counterfeit_similarity: float,
    ood_score: float,
    db_session: AsyncSession,
) -> RegionScore:
    """Score a single region and publish the result to the decision queue."""

    # Determine region decision
    if authentic_similarity >= 0.85 and counterfeit_similarity < 0.50:
        region_decision = "STRONG_MATCH"
    elif authentic_similarity >= 0.70:
        region_decision = "MODERATE_MATCH"
    elif authentic_similarity >= 0.50:
        region_decision = "WEAK_MATCH"
    elif counterfeit_similarity > authentic_similarity:
        region_decision = "MISMATCH"
    else:
        region_decision = "INCONCLUSIVE"

    region_score_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Insert into region_scores table
    await db_session.execute(
        text(
            """
            INSERT INTO region_scores (
                id, scan_session_id, image_asset_id, region_code,
                authentic_similarity, counterfeit_similarity, ood_score,
                region_decision, created_at
            ) VALUES (
                :id, :scan_session_id, :image_asset_id, :region_code,
                :authentic_similarity, :counterfeit_similarity, :ood_score,
                :region_decision, :created_at
            )
            """
        ),
        {
            "id": region_score_id,
            "scan_session_id": scan_session_id,
            "image_asset_id": image_asset_id,
            "region_code": region_code,
            "authentic_similarity": authentic_similarity,
            "counterfeit_similarity": counterfeit_similarity,
            "ood_score": ood_score,
            "region_decision": region_decision,
            "created_at": now,
        },
    )
    await db_session.commit()

    score = RegionScore(
        scan_session_id=scan_session_id,
        image_asset_id=image_asset_id,
        region_code=region_code,
        authentic_similarity=authentic_similarity,
        counterfeit_similarity=counterfeit_similarity,
        ood_score=ood_score,
        region_decision=region_decision,
    )

    # Record audit event
    await record_audit_event(
        db_session,
        "REGION_SCORED",
        image_id=UUID(image_asset_id),
        payload={
            "region_code": region_code,
            "region_decision": region_decision,
            "authentic_similarity": authentic_similarity,
            "counterfeit_similarity": counterfeit_similarity,
        },
    )

    # Publish event to decision queue
    envelope = EventEnvelope(
        event_type=EventTypes.REGION_SCORED,
        correlation_id=get_correlation_id(),
        scan_session_id=UUID(scan_session_id),
        image_id=UUID(image_asset_id),
        region_code=region_code,
        source_service=settings.service_name,
        payload={
            "region_score_id": region_score_id,
            "scan_session_id": scan_session_id,
            "image_asset_id": image_asset_id,
            "region_code": region_code,
            "authentic_similarity": authentic_similarity,
            "counterfeit_similarity": counterfeit_similarity,
            "ood_score": ood_score,
            "region_decision": region_decision,
        },
    )
    send_message("decision-queue", envelope)

    logger.info(
        "region_scored",
        region_score_id=region_score_id,
        scan_session_id=scan_session_id,
        region_code=region_code,
        region_decision=region_decision,
    )

    return score
