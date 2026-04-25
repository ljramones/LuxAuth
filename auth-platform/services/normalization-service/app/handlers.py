from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import NormalizationResult
from auth_common.s3 import download_file, upload_file

from app.settings import settings

logger = get_logger(settings.service_name)

PREPROCESSING_VERSION = "normalize_stub_v0.1.0"


async def normalize_image(
    image_asset_id: UUID, db_session: AsyncSession
) -> NormalizationResult:
    """Download a raw image, apply stub normalization, and upload the result."""

    # Look up scan_session_id and raw_object_uri from image_assets
    row = await db_session.execute(
        text("SELECT scan_session_id, raw_object_uri FROM image_assets WHERE id = :id"),
        {"id": str(image_asset_id)},
    )
    asset = row.mappings().one_or_none()
    if asset is None:
        raise ValueError(f"image_asset_id {image_asset_id} not found")

    scan_session_id = asset["scan_session_id"]
    raw_object_uri = asset["raw_object_uri"]  # e.g. s3://bucket/key

    # Extract S3 key from URI
    # raw_object_uri format: s3://bucket-name/path/to/file
    uri_parts = raw_object_uri.replace("s3://", "").split("/", 1)
    raw_bucket = uri_parts[0]
    raw_key = uri_parts[1]

    # Download raw image from S3
    raw_bytes = download_file(raw_bucket, raw_key)

    # Stub normalization: pass through bytes unchanged
    normalized_bytes = raw_bytes

    # Upload normalized image
    normalized_key = f"{scan_session_id}/{image_asset_id}_normalized.bin"
    normalized_uri = upload_file(
        settings.s3_normalized_bucket,
        normalized_key,
        normalized_bytes,
        content_type="application/octet-stream",
    )

    # Persist to normalized_images table
    await db_session.execute(
        text(
            """
            INSERT INTO normalized_images (id, image_asset_id, normalized_object_uri, preprocessing_version)
            VALUES (:id, :image_asset_id, :uri, :version)
            ON CONFLICT (image_asset_id) DO UPDATE SET
                normalized_object_uri = EXCLUDED.normalized_object_uri,
                preprocessing_version = EXCLUDED.preprocessing_version
            """
        ),
        {
            "id": str(uuid4()),
            "image_asset_id": str(image_asset_id),
            "uri": normalized_uri,
            "version": PREPROCESSING_VERSION,
        },
    )
    await db_session.commit()

    # Publish downstream event
    envelope = EventEnvelope(
        event_type=EventTypes.IMAGE_NORMALIZED,
        scan_session_id=scan_session_id,
        image_id=image_asset_id,
        payload={
            "image_asset_id": str(image_asset_id),
            "scan_session_id": str(scan_session_id),
            "normalized_object_uri": normalized_uri,
        },
    )
    send_message(settings.sqs_embedding_queue, envelope)
    logger.info("normalization_complete", image_asset_id=str(image_asset_id))

    return NormalizationResult(
        image_asset_id=image_asset_id,
        normalized_object_uri=normalized_uri,
        preprocessing_version=PREPROCESSING_VERSION,
    )
