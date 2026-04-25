import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.database import get_db
from auth_common.events import EventEnvelope, EventTypes
from auth_common.imaging import validate_image
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


async def _get_valid_regions(scan_session_id: uuid.UUID, db: AsyncSession) -> list[str]:
    """Look up the scan recipe for this session and return valid region codes."""
    result = await db.execute(
        text(
            """
            SELECT srr.region_code
            FROM scan_sessions ss
            JOIN scan_recipe_regions srr ON srr.scan_recipe_id = ss.scan_recipe_id
            WHERE ss.id = :session_id
            ORDER BY srr.sort_order
            """
        ),
        {"session_id": str(scan_session_id)},
    )
    return [row["region_code"] for row in result.mappings()]


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
    # Validate session exists and get organization_id
    session_result = await db.execute(
        text("SELECT id, status, organization_id FROM scan_sessions WHERE id = :id"),
        {"id": str(scan_session_id)},
    )
    session_row = session_result.mappings().first()
    if not session_row:
        raise HTTPException(status_code=404, detail="Scan session not found")

    org_id = session_row["organization_id"]

    # Validate region code against recipe
    valid_regions = await _get_valid_regions(scan_session_id, db)
    if valid_regions and region_code not in valid_regions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid region_code '{region_code}'. Valid regions: {valid_regions}",
        )

    image_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Read file content
    content = await file.read()

    # Validate image using real image processing
    validation = validate_image(content)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid image", "issues": validation["issues"]},
        )

    # Checksums
    checksum_md5 = hashlib.md5(content).hexdigest()  # noqa: S324
    sha256_checksum = validation["sha256_checksum"]
    file_size = validation["file_size_bytes"]
    width = validation["width"]
    height = validation["height"]
    image_format = validation["image_format"]
    color_mode = validation["color_mode"]

    # Derive file extension from format
    ext_map = {"JPEG": "jpg", "PNG": "png", "TIFF": "tiff", "BMP": "bmp", "WEBP": "webp"}
    ext = ext_map.get(image_format, "bin")

    # Upload to S3 with proper key structure
    s3_key = f"scans/{org_id}/{scan_session_id}/raw/{image_id}.{ext}"
    raw_object_uri = upload_file(
        bucket=settings.raw_evidence_bucket,
        key=s3_key,
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )

    # Store metadata in DB (including new image validation columns)
    await db.execute(
        text(
            """
            INSERT INTO image_assets (id, scan_session_id, region_code, device_id,
                                      raw_object_uri, checksum, file_size_bytes,
                                      content_type, width, height, image_format,
                                      color_mode, sha256_checksum, created_at)
            VALUES (:id, :session_id, :region_code, :device_id,
                    :raw_uri, :checksum, :file_size,
                    :content_type, :width, :height, :image_format,
                    :color_mode, :sha256_checksum, :created_at)
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
            "content_type": file.content_type or "application/octet-stream",
            "width": width,
            "height": height,
            "image_format": image_format,
            "color_mode": color_mode,
            "sha256_checksum": sha256_checksum,
            "created_at": now,
        },
    )

    # Update session status to CAPTURING
    if session_row["status"] == "CREATED":
        await db.execute(
            text("UPDATE scan_sessions SET status = 'CAPTURING', updated_at = :now WHERE id = :id"),
            {"id": str(scan_session_id), "now": now},
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
            "sha256_checksum": sha256_checksum,
            "file_size_bytes": file_size,
        },
    )
    try:
        send_message(settings.image_upload_queue, envelope)
    except Exception:
        logger.warning("failed_to_publish_event", image_id=str(image_id))

    await record_audit_event(
        db,
        "IMAGE_UPLOADED",
        scan_session_id=scan_session_id,
        image_id=image_id,
        payload={"region_code": region_code, "checksum": checksum_md5, "sha256_checksum": sha256_checksum},
    )

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
        {"session_id": str(scan_session_id)},
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
