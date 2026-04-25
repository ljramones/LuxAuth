from auth_common.database import get_db
from auth_common.logging import get_logger
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers import score_region
from app.settings import settings

logger = get_logger(settings.service_name)
router = APIRouter()


class ScoreRequest(BaseModel):
    image_asset_id: str
    scan_session_id: str
    region_code: str
    authentic_similarity: float
    counterfeit_similarity: float
    ood_score: float


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready", "service": settings.service_name}


@router.post("/score")
async def post_score(body: ScoreRequest, db: AsyncSession = Depends(get_db)):
    result = await score_region(
        image_asset_id=body.image_asset_id,
        scan_session_id=body.scan_session_id,
        region_code=body.region_code,
        authentic_similarity=body.authentic_similarity,
        counterfeit_similarity=body.counterfeit_similarity,
        ood_score=body.ood_score,
        db_session=db,
    )
    return result


@router.get("/scores/{scan_session_id}")
async def get_scores(scan_session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM region_scores WHERE scan_session_id = :sid ORDER BY created_at"),
        {"sid": scan_session_id},
    )
    rows = result.mappings().all()
    return {"scan_session_id": scan_session_id, "scores": [dict(r) for r in rows]}
