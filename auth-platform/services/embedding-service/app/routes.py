import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from auth_common.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers import generate_embedding

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "embedding-service"}


@router.get("/ready")
async def ready() -> dict:
    return {"status": "ready", "service": "embedding-service"}


@router.post("/process/{image_asset_id}")
async def process(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    record = await generate_embedding(image_asset_id, db)
    return record


@router.get("/embeddings/{image_asset_id}")
async def get_embedding(image_asset_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            """
            SELECT image_asset_id, embedding_model_version,
                   created_at
            FROM embeddings
            WHERE image_asset_id = :id
            """
        ),
        {"id": str(image_asset_id)},
    )
    row = result.mappings().one_or_none()
    if row is None:
        return {"detail": "embedding not found"}, 404
    return dict(row)
