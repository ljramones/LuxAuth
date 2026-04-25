import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from auth_common.correlation import get_correlation_id
from auth_common.database import get_db
from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import ImageAssetResponse
from auth_common.s3 import upload_file

logger = get_logger(settings.service_name)

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready"}


@router.post(
    "/scan-sessions/{scan_session_id}/images",
    response_model=ImageAssetResponse,
    status_code=201,
)
async def upload_image(
    scan_session_id: uuid.UUID,
    file: UploadFile,
    region_code: str = Form(...),
    device_id: uuid.UUID = Form(...),
    db: AsyncSession = Depends(get_db),
):
    image_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Read file content and compute checksum
    content = await file.read()
    checksum_md5 = hashlib.md5(content).hexdigest()  # noqa: S324
    file_size = len(content)

    # Upload to S3
    s3_key = f"{scan_session_id}/{image_id}.bin"
    raw_object_uri = upload_file(
        bucket=settings.raw_evidence_bucket,
        key=s3_key,
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )

    # Store metadata in DB
    await db.execute(
        text(
            """
            INSERT INTO image_assets (id, scan_session_id, region_code, device_id,
                                      raw_object_uri, checksum, file_size_bytes, created_at)
            VALUES (:id, :session_id, :region_code, :device_id,
                    :raw_uri, :checksum, :file_size, :created_at)
            """
        ),
        {
            "id": image_id,
            "session_id": scan_session_id,
            "region_code": region_code,
            "device_id": device_id,
            "raw_uri": raw_object_uri,
            "checksum": checksum_md5,
            "file_size": file_size,
            "created_at": now,
        },
    )

    # Publish IMAGE_UPLOADED event
    envelope = EventEnvelope(
        event_type=EventTypes.IMAGE_UPLOADED,
        correlation_id=get_correlation_id(),
        scan_session_id=scan_session_id,
        image_id=image_id,
        payload={
            "region_code": region_code,
            "raw_object_uri": raw_object_uri,
            "checksum": checksum_md5,
            "file_size_bytes": file_size,
        },
    )
    try:
        send_message(settings.image_upload_queue, envelope)
    except Exception:
        logger.warning("failed_to_publish_event", image_id=str(image_id))

    # TODO: record audit event

    logger.info("image_uploaded", image_id=str(image_id), scan_session_id=str(scan_session_id))

    return ImageAssetResponse(
        id=image_id,
        scan_session_id=scan_session_id,
        region_code=region_code,
        raw_object_uri=raw_object_uri,
        checksum=checksum_md5,
        file_size_bytes=file_size,
        created_at=now,
    )


@router.get(
    "/scan-sessions/{scan_session_id}/images",
    response_model=list[ImageAssetResponse],
)
async def list_images(
    scan_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM image_assets WHERE scan_session_id = :session_id ORDER BY created_at"),
        {"session_id": scan_session_id},
    )
    rows = result.mappings().all()
    return [
        ImageAssetResponse(
            id=row["id"],
            scan_session_id=row["scan_session_id"],
            region_code=row["region_code"],
            raw_object_uri=row["raw_object_uri"],
            checksum=row["checksum"],
            file_size_bytes=row["file_size_bytes"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
