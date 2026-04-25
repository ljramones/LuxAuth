import uuid

from auth_common.database import get_db
from auth_common.logging import get_logger
from auth_common.models import ScanRecipeRegion, ScanRecipeResponse
from fastapi import APIRouter, Depends, HTTPException, Query
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


async def _build_recipe_response(row: dict, db: AsyncSession) -> ScanRecipeResponse:
    """Build a ScanRecipeResponse including its regions from the DB."""
    region_result = await db.execute(
        text(
            "SELECT region_code, display_name, min_images, magnification_profile, lighting_profile "
            "FROM scan_recipe_regions WHERE scan_recipe_id = :recipe_id ORDER BY sort_order"
        ),
        {"recipe_id": row["id"]},
    )
    regions = [
        ScanRecipeRegion(
            region_code=r["region_code"],
            display_name=r["display_name"],
            min_images=r["min_images"],
            magnification_profile=r["magnification_profile"],
            lighting_profile=r["lighting_profile"],
        )
        for r in region_result.mappings()
    ]
    return ScanRecipeResponse(
        id=row["id"],
        recipe_key=row["recipe_key"],
        brand=row["brand"],
        category=row["category"],
        material=row["material"],
        version=row["version"],
        regions=regions,
    )


@router.get("/scan-recipes/resolve", response_model=ScanRecipeResponse)
async def resolve_recipe(
    brand: str = Query(...),
    category: str = Query(...),
    material: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text(
            "SELECT * FROM scan_recipes "
            "WHERE brand = :brand AND category = :category AND material = :material "
            "AND is_active = true "
            "ORDER BY version DESC LIMIT 1"
        ),
        {"brand": brand, "category": category, "material": material},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="No matching recipe found")

    return await _build_recipe_response(dict(row), db)


@router.get("/scan-recipes/{recipe_id}", response_model=ScanRecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM scan_recipes WHERE id = :id"),
        {"id": recipe_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return await _build_recipe_response(dict(row), db)
