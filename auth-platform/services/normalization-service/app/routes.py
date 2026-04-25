import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.database import get_db

from app.handlers import normalize_image

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "normalization-service"}


@router.get("/ready")
async def ready() -> dict:
    return {"status": "ready", "service": "normalization-service"}


@router.post("/process/{image_asset_id}")
async def process(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await normalize_image(image_asset_id, db)
    return result


@router.get("/results/{image_asset_id}")
async def get_result(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            """
            SELECT image_asset_id, s3_key, preprocessing_version
            FROM normalized_images
            WHERE image_asset_id = :id
            """
        ),
        {"id": str(image_asset_id)},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return {"detail": "normalization result not found"}, 404
    return dict(row)
