import uuid
from datetime import UTC, datetime

import httpx
from auth_common.audit import record_audit_event
from auth_common.database import get_db
from auth_common.logging import get_logger
from auth_common.models import ScanSessionCreate, ScanSessionResponse
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


async def _get_recipe_regions(recipe_id: str, db: AsyncSession) -> list[str]:
    """Fetch region codes for a recipe from the database."""
    result = await db.execute(
        text(
            "SELECT region_code FROM scan_recipe_regions "
            "WHERE scan_recipe_id = :recipe_id ORDER BY sort_order"
        ),
        {"recipe_id": recipe_id},
    )
    return [row["region_code"] for row in result.mappings()]


@router.post("/scan-sessions", response_model=ScanSessionResponse, status_code=201)
async def create_scan_session(
    body: ScanSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    session_id = uuid.uuid4()
    now = datetime.now(UTC)

    recipe = await _resolve_recipe(
        body.claimed_brand, body.claimed_category, body.claimed_material
    )

    if not recipe:
        raise HTTPException(
            status_code=400,
            detail=f"No scan recipe found for brand={body.claimed_brand}, "
                   f"category={body.claimed_category}, material={body.claimed_material}",
        )

    recipe_id = recipe["id"]
    regions = recipe.get("regions", [])
    required_regions = [r["region_code"] for r in regions]

    await db.execute(
        text(
            """
            INSERT INTO scan_sessions
                (id, status, claimed_brand, claimed_category, claimed_material,
                 claimed_model, device_id, organization_id, scan_recipe_id, created_at, updated_at)
            VALUES
                (:id, 'CREATED', :brand, :category, :material,
                 :model, :device_id, :org_id, :recipe_id, :now, :now)
            """
        ),
        {
            "id": session_id,
            "brand": body.claimed_brand,
            "category": body.claimed_category,
            "material": body.claimed_material,
            "model": body.claimed_model,
            "device_id": str(body.device_id),
            "org_id": str(body.organization_id),
            "recipe_id": recipe_id,
            "now": now,
        },
    )

    await record_audit_event(
        db,
        "SCAN_CREATED",
        scan_session_id=session_id,
        tenant_id=body.organization_id,
        payload={"claimed_brand": body.claimed_brand, "recipe_id": recipe_id},
    )

    logger.info("scan_session_created", session_id=str(session_id), recipe_id=recipe_id)

    return ScanSessionResponse(
        id=session_id,
        status="CREATED",
        claimed_brand=body.claimed_brand,
        claimed_category=body.claimed_category,
        claimed_material=body.claimed_material,
        claimed_model=body.claimed_model,
        scan_recipe_id=recipe_id,
        required_regions=required_regions,
        created_at=now,
    )


@router.get("/scan-sessions/{scan_session_id}")
async def get_scan_session(
    scan_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM scan_sessions WHERE id = :id"),
        {"id": str(scan_session_id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Scan session not found")

    required_regions = []
    if row["scan_recipe_id"]:
        required_regions = await _get_recipe_regions(str(row["scan_recipe_id"]), db)

    return ScanSessionResponse(
        id=row["id"],
        status=row["status"],
        claimed_brand=row["claimed_brand"],
        claimed_category=row["claimed_category"],
        claimed_material=row["claimed_material"],
        claimed_model=row.get("claimed_model"),
        scan_recipe_id=row["scan_recipe_id"],
        required_regions=required_regions,
        created_at=row["created_at"],
    )
