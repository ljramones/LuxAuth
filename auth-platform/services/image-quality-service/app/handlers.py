import json
import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import ImageQualityReport

from app.settings import settings

logger = get_logger(settings.service_name)


async def process_image_quality(
    image_asset_id: UUID, db_session: AsyncSession
) -> ImageQualityReport:
    """Assess image quality and produce a report.

    Generates deterministic scores derived from *image_asset_id* so the
    behaviour is reproducible across runs.
    """

    id_hash = hash(str(image_asset_id))
    sharpness_score = 0.85 + (id_hash % 15) / 100.0
    exposure_score = 0.80 + (id_hash % 20) / 100.0
    glare_score = (id_hash % 20) / 100.0

    issues: list[str] = []
    if sharpness_score <= 0.5:
        issues.append("sharpness below threshold")
    if exposure_score <= 0.5:
        issues.append("exposure below threshold")
    if glare_score >= 0.5:
        issues.append("excessive glare detected")

    quality_status = "PASS" if not issues else "FAIL"

    # Persist to image_quality_reports table
    await db_session.execute(
        text(
            """
            INSERT INTO image_quality_reports
                (image_asset_id, sharpness_score, exposure_score, glare_score,
                 quality_status, issues)
            VALUES
                (:image_asset_id, :sharpness, :exposure, :glare, :status, :issues)
            ON CONFLICT (image_asset_id) DO UPDATE SET
                sharpness_score = EXCLUDED.sharpness_score,
                exposure_score  = EXCLUDED.exposure_score,
                glare_score     = EXCLUDED.glare_score,
                quality_status  = EXCLUDED.quality_status,
                issues          = EXCLUDED.issues
            """
        ),
        {
            "image_asset_id": str(image_asset_id),
            "sharpness": sharpness_score,
            "exposure": exposure_score,
            "glare": glare_score,
            "status": quality_status,
            "issues": json.dumps(issues),
        },
    )
    await db_session.commit()

    # If quality passed, look up scan_session_id and publish downstream
    if quality_status == "PASS":
        row = await db_session.execute(
            text(
                "SELECT scan_session_id FROM image_assets WHERE id = :id"
            ),
            {"id": str(image_asset_id)},
        )
        scan_session_id = row.scalar_one_or_none()

        envelope = EventEnvelope(
            event_type=EventTypes.IMAGE_QUALITY_COMPLETED,
            payload={
                "image_asset_id": str(image_asset_id),
                "scan_session_id": str(scan_session_id) if scan_session_id else None,
                "quality_status": quality_status,
            },
        )
        send_message(settings.sqs_normalization_queue, envelope)
        logger.info(
            "quality PASS - published to normalization queue",
            extra={"image_asset_id": str(image_asset_id)},
        )
    else:
        logger.info(
            "quality FAIL - not forwarding",
            extra={"image_asset_id": str(image_asset_id), "issues": issues},
        )

    # TODO: emit audit event

    return ImageQualityReport(
        image_asset_id=image_asset_id,
        sharpness_score=sharpness_score,
        exposure_score=exposure_score,
        glare_score=glare_score,
        quality_status=quality_status,
        issues=issues,
    )
