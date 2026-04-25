import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from auth_common.database import get_db
from auth_common.logging import get_logger
from auth_common.models import DeviceRegister, DeviceResponse

logger = get_logger(settings.service_name)

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready"}


@router.post("/devices/register", response_model=DeviceResponse, status_code=201)
async def register_device(
    body: DeviceRegister,
    db: AsyncSession = Depends(get_db),
):
    device_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    await db.execute(
        text(
            """
            INSERT INTO devices (id, device_serial, device_type, organization_id, firmware_version, status, created_at)
            VALUES (:id, :device_serial, :device_type, :org_id, :firmware_version, :status, :created_at)
            """
        ),
        {
            "id": device_id,
            "device_serial": body.device_serial,
            "device_type": body.device_type,
            "org_id": body.organization_id,
            "firmware_version": body.firmware_version,
            "status": "active",
            "created_at": now,
        },
    )
    # TODO: record audit event

    logger.info("device_registered", device_id=str(device_id))

    return DeviceResponse(
        id=device_id,
        device_serial=body.device_serial,
        device_type=body.device_type,
        status="active",
        firmware_version=body.firmware_version,
        created_at=now,
    )


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM devices WHERE id = :id"),
        {"id": device_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")

    return DeviceResponse(
        id=row["id"],
        device_serial=row["device_serial"],
        device_type=row["device_type"],
        status=row["status"],
        firmware_version=row.get("firmware_version"),
        created_at=row["created_at"],
    )
