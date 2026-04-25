import json
import uuid
from datetime import UTC, datetime

from auth_common.audit import record_audit_event
from auth_common.database import get_db
from auth_common.logging import get_logger
from auth_common.models import DeviceRegister, DeviceResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings

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
    now = datetime.now(UTC)

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
    await record_audit_event(db, "DEVICE_REGISTERED", payload={"device_id": str(device_id), "device_serial": body.device_serial})

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


@router.post("/devices/{device_id}/calibrations", status_code=201)
async def create_calibration(
    device_id: uuid.UUID,
    body: dict,  # Accept flexible JSON for calibration profile
    db: AsyncSession = Depends(get_db),
):
    # Verify device exists
    dev = await db.execute(text("SELECT id FROM devices WHERE id = :id"), {"id": str(device_id)})
    if not dev.first():
        raise HTTPException(status_code=404, detail="Device not found")

    cal_id = uuid.uuid4()
    now = datetime.now(UTC)

    await db.execute(
        text("""
            INSERT INTO device_calibrations (id, device_id, calibration_profile, calibrated_at, expires_at)
            VALUES (:id, :device_id, :profile, :calibrated_at, :expires_at)
        """),
        {
            "id": cal_id,
            "device_id": device_id,
            "profile": json.dumps(body.get("calibration_profile", body)),
            "calibrated_at": now,
            "expires_at": datetime(2027, 1, 1, tzinfo=UTC),
        },
    )

    await record_audit_event(db, "DEVICE_CALIBRATION_CREATED", payload={"device_id": str(device_id), "calibration_id": str(cal_id)})

    return {"id": str(cal_id), "device_id": str(device_id), "calibrated_at": now.isoformat(), "status": "active"}


@router.get("/devices/{device_id}/calibrations/{calibration_id}")
async def get_calibration(
    device_id: uuid.UUID,
    calibration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM device_calibrations WHERE id = :id AND device_id = :did"),
        {"id": str(calibration_id), "did": str(device_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Calibration not found")
    return dict(row)
