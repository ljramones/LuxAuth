import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from auth_common.database import get_db
from auth_common.logging import get_logger
from auth_common.models import ScanSessionCreate, ScanSessionResponse

logger = get_logger(settings.service_name)

router = APIRouter()

FALLBACK_REGIONS = ["front_logo", "interior_stamp", "hardware_closeup", "stitching_detail"]


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready"}


async def _resolve_recipe(brand: str, category: str, material: str) -> dict | None:
    """Call scan-recipe-service to resolve a recipe; return None on failure."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.scan_recipe_service_url}/scan-recipes/resolve",
                params={"brand": brand, "category": category, "material": material},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        logger.warning("scan_recipe_service_unavailable", brand=brand)
    return None


@router.post("/scan-sessions", response_model=ScanSessionResponse, status_code=201)
async def create_scan_session(
    body: ScanSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    recipe = await _resolve_recipe(body.claimed_brand, body.claimed_category, body.claimed_material)

    recipe_id = None
    required_regions = FALLBACK_REGIONS
    if recipe:
        recipe_id = recipe.get("id")
        regions = recipe.get("regions", [])
        if regions:
            required_regions = [r["region_code"] for r in regions]

    await db.execute(
        text(
            """
            INSERT INTO scan_sessions (id, status, claimed_brand, claimed_category, claimed_material, device_id,
                                       organization_id, scan_recipe_id, created_at)
            VALUES (:id, :status, :brand, :category, :material, :device_id,
                    :org_id, :recipe_id, :created_at)
            """
        ),
        {
            "id": session_id,
            "status": "pending",
            "brand": body.claimed_brand,
            "category": body.claimed_category,
            "material": body.claimed_material,
            "device_id": body.device_id,
            "org_id": body.organization_id,
            "recipe_id": recipe_id,
            "created_at": now,
        },
    )
    # TODO: record audit event

    logger.info("scan_session_created", session_id=str(session_id))

    return ScanSessionResponse(
        id=session_id,
        status="pending",
        claimed_brand=body.claimed_brand,
        claimed_category=body.claimed_category,
        claimed_material=body.claimed_material,
        scan_recipe_id=recipe_id,
        required_regions=required_regions,
        created_at=now,
    )


@router.get("/scan-sessions/{scan_session_id}", response_model=ScanSessionResponse)
async def get_scan_session(
    scan_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM scan_sessions WHERE id = :id"),
        {"id": scan_session_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Scan session not found")

    return ScanSessionResponse(
        id=row["id"],
        status=row["status"],
        claimed_brand=row["claimed_brand"],
        claimed_category=row["claimed_category"],
        claimed_material=row["claimed_material"],
        scan_recipe_id=row.get("scan_recipe_id"),
        required_regions=[],
        created_at=row["created_at"],
    )
