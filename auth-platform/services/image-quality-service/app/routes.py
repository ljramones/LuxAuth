import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from auth_common.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers import process_image_quality

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "image-quality-service"}


@router.get("/ready")
async def ready() -> dict:
    return {"status": "ready", "service": "image-quality-service"}


@router.post("/process/{image_asset_id}")
async def process(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    report = await process_image_quality(image_asset_id, db)
    return report


@router.get("/reports/{image_asset_id}")
async def get_report(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            """
            SELECT image_asset_id, sharpness_score, exposure_score,
                   glare_score, quality_status, issues, created_at
            FROM image_quality_reports
            WHERE image_asset_id = :id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"id": str(image_asset_id)},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    return dict(row)
