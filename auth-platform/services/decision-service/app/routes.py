from auth_common.database import get_db
from auth_common.logging import get_logger
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers import make_decision
from app.settings import settings

logger = get_logger(settings.service_name)
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready", "service": settings.service_name}


@router.post("/decide/{scan_session_id}")
async def post_decide(scan_session_id: str, db: AsyncSession = Depends(get_db)):
    decision = await make_decision(scan_session_id, db)
    return decision


@router.get("/decisions/{scan_session_id}")
async def get_decision(scan_session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM authentication_decisions WHERE scan_session_id = :sid"),
        {"sid": scan_session_id},
    )
    row = result.mappings().first()
    if not row:
        return {"error": "Decision not found"}, 404
    return dict(row)
