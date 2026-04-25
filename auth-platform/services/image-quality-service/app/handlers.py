import json
from uuid import UUID

from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.events import EventEnvelope, EventTypes
from auth_common.imaging import compute_quality_metrics
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import ImageQualityReport
from auth_common.s3 import download_file
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings

logger = get_logger(settings.service_name)


async def process_image_quality(
    image_asset_id: UUID, db_session: AsyncSession
) -> ImageQualityReport:
    """Assess image quality using real computer vision metrics."""

    # Look up raw image location
    row = await db_session.execute(
        text("SELECT scan_session_id, raw_object_uri FROM image_assets WHERE id = :id"),
        {"id": str(image_asset_id)},
    )
    asset = row.mappings().one_or_none()
    if asset is None:
        raise ValueError(f"image_asset_id {image_asset_id} not found")

    scan_session_id = asset["scan_session_id"]
    raw_uri = asset["raw_object_uri"]

    # Download raw image from S3
    uri_parts = raw_uri.replace("s3://", "").split("/", 1)
    raw_bytes = download_file(uri_parts[0], uri_parts[1])

    # Compute real quality metrics
    metrics = compute_quality_metrics(raw_bytes)

    sharpness_score = metrics["sharpness_score"]
    exposure_score = metrics["exposure_score"]
    glare_score = metrics["glare_score"]
    quality_status = metrics["quality_status"]
    issues = metrics["issues"]

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

    # If quality passed, publish downstream
    if quality_status == "PASS":
        envelope = EventEnvelope(
            event_type=EventTypes.IMAGE_QUALITY_COMPLETED,
            correlation_id=get_correlation_id(),
            scan_session_id=scan_session_id,
            image_id=image_asset_id,
            source_service=settings.service_name,
            payload={
                "image_asset_id": str(image_asset_id),
                "scan_session_id": str(scan_session_id),
                "quality_status": quality_status,
            },
        )
        send_message(settings.sqs_normalization_queue, envelope)
        logger.info("quality_pass", image_asset_id=str(image_asset_id))
    else:
        logger.info("quality_fail", image_asset_id=str(image_asset_id), issues=issues)

    await record_audit_event(
        db_session,
        "IMAGE_QUALITY_COMPLETED",
        image_id=image_asset_id,
        scan_session_id=scan_session_id,
        payload={"quality_status": quality_status, "sharpness_score": sharpness_score, "issues": issues},
    )

    return ImageQualityReport(
        image_asset_id=image_asset_id,
        sharpness_score=sharpness_score,
        exposure_score=exposure_score,
        glare_score=glare_score,
        quality_status=quality_status,
        issues=issues,
    )
