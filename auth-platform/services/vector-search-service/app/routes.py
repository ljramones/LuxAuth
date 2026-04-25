import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.database import get_db

from app.handlers import search_similar

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "vector-search-service"}


@router.get("/ready")
async def ready() -> dict:
    return {"status": "ready", "service": "vector-search-service"}


@router.post("/search/{image_asset_id}")
async def search(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await search_similar(image_asset_id, db)
    return result


@router.get("/results/{image_asset_id}")
async def get_result(image_asset_id: UUID):
    # TODO: persist and retrieve cached search results from DB
    return {"detail": "result caching not yet implemented", "image_asset_id": str(image_asset_id)}
