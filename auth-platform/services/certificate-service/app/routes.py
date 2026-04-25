import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.database import get_db
from auth_common.logging import get_logger
from auth_common.models import CertificateResponse

from app.settings import settings

logger = get_logger(settings.service_name)
router = APIRouter()


class CreateCertificateRequest(BaseModel):
    scan_session_id: str


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready", "service": settings.service_name}


@router.post("/certificates")
async def create_certificate(body: CreateCertificateRequest, db: AsyncSession = Depends(get_db)):
    # Look up authentication decision for this scan session
    result = await db.execute(
        text("SELECT * FROM authentication_decisions WHERE scan_session_id = :sid ORDER BY created_at DESC LIMIT 1"),
        {"sid": body.scan_session_id},
    )
    decision = result.mappings().first()

    if not decision:
        raise HTTPException(status_code=404, detail="No authentication decision found for this scan session")

    if decision["result"] != "VERIFIED":
        raise HTTPException(status_code=400, detail="Cannot issue certificate for non-verified scan")

    certificate_id = str(uuid.uuid4())
    certificate_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    await db.execute(
        text(
            """
            INSERT INTO certificates (
                id, scan_session_id, authentication_decision_id,
                certificate_number, created_at
            ) VALUES (
                :id, :scan_session_id, :authentication_decision_id,
                :certificate_number, :created_at
            )
            """
        ),
        {
            "id": certificate_id,
            "scan_session_id": body.scan_session_id,
            "authentication_decision_id": decision["id"],
            "certificate_number": certificate_number,
            "created_at": now,
        },
    )
    await db.commit()

    logger.info(
        "certificate_issued",
        certificate_id=certificate_id,
        certificate_number=certificate_number,
        scan_session_id=body.scan_session_id,
    )

    return CertificateResponse(
        id=certificate_id,
        scan_session_id=body.scan_session_id,
        authentication_decision_id=str(decision["id"]),
        certificate_number=certificate_number,
        created_at=now,
    )


@router.get("/certificates/{certificate_id}")
async def get_certificate(certificate_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM certificates WHERE id = :id"),
        {"id": certificate_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return dict(row)


@router.get("/certificates/verify/{certificate_number}")
async def verify_certificate(certificate_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM certificates WHERE certificate_number = :cn"),
        {"cn": certificate_number},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return {"valid": True, "certificate": dict(row)}
