"""Read-only data explorer endpoints."""

from auth_common.database import get_db
from auth_common.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings

logger = get_logger(settings.service_name)
data_router = APIRouter(prefix="/data", tags=["data-explorer"])


# ── Overview ────────────────────────────────────────────────────────

@data_router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)):
    """Global data inventory summary."""
    queries = {
        "datasets": "SELECT count(*) FROM reference_dataset_versions",
        "reference_items": "SELECT count(*) FROM reference_items",
        "reference_images": "SELECT count(*) FROM reference_images",
        "embeddings": "SELECT count(*) FROM reference_embeddings",
        "capture_batches": "SELECT count(*) FROM capture_batches",
        "quality_reports_pass": "SELECT count(*) FROM image_quality_reports WHERE quality_status = 'PASS'",
        "quality_reports_fail": "SELECT count(*) FROM image_quality_reports WHERE quality_status = 'FAIL'",
        "condition_metadata": "SELECT count(*) FROM item_condition_metadata",
        "component_conditions": "SELECT count(*) FROM item_component_conditions",
    }
    counts: dict[str, int] = {}
    for key, q in queries.items():
        r = await db.execute(text(q))
        counts[key] = r.scalar() or 0

    # Datasets by status
    ds_status = await db.execute(text(
        "SELECT status, count(*) as cnt FROM reference_dataset_versions GROUP BY status"
    ))
    counts["datasets_by_status"] = {r["status"]: r["cnt"] for r in ds_status.mappings()}  # type: ignore[assignment]

    # Datasets by source_type
    ds_source = await db.execute(text(
        "SELECT source_type, count(*) as cnt FROM reference_dataset_versions GROUP BY source_type"
    ))
    counts["datasets_by_source"] = {r["source_type"]: r["cnt"] for r in ds_source.mappings()}  # type: ignore[assignment]

    # Embeddings by model
    emb_model = await db.execute(text(
        "SELECT embedding_model_version, count(*) as cnt FROM reference_embeddings GROUP BY embedding_model_version"
    ))
    counts["embeddings_by_model"] = {r["embedding_model_version"]: r["cnt"] for r in emb_model.mappings()}  # type: ignore[assignment]

    return counts


# ── Dataset List ────────────────────────────────────────────────────

@data_router.get("/datasets")
async def list_datasets_detailed(db: AsyncSession = Depends(get_db)):
    """Dataset inventory with counts and metadata."""
    result = await db.execute(text("""
        SELECT rdv.id, rdv.dataset_version, rdv.status, rdv.source_type, rdv.created_at,
               count(rdm.id) as image_count,
               count(rdm.id) FILTER (WHERE rdm.split = 'train') as train_count,
               count(rdm.id) FILTER (WHERE rdm.split = 'validation') as validation_count,
               count(rdm.id) FILTER (WHERE rdm.split = 'test') as test_count
        FROM reference_dataset_versions rdv
        LEFT JOIN reference_dataset_members rdm ON rdm.dataset_version_id = rdv.id
        GROUP BY rdv.id ORDER BY rdv.created_at DESC
    """))
    datasets = []
    for row in result.mappings():
        ds_id = str(row["id"])

        # Regions
        reg = await db.execute(text("""
            SELECT DISTINCT ri.region_code FROM reference_dataset_members rdm
            JOIN reference_images ri ON ri.id = rdm.reference_image_id
            WHERE rdm.dataset_version_id = :id
        """), {"id": ds_id})
        regions = [r["region_code"] for r in reg.mappings()]

        # Labels
        lab = await db.execute(text("""
            SELECT DISTINCT rit.authenticity_status FROM reference_dataset_members rdm
            JOIN reference_images ri ON ri.id = rdm.reference_image_id
            JOIN reference_items rit ON rit.id = ri.reference_item_id
            WHERE rdm.dataset_version_id = :id
        """), {"id": ds_id})
        labels = [r["authenticity_status"] for r in lab.mappings()]

        # Items
        items = await db.execute(text("""
            SELECT count(DISTINCT ri.reference_item_id) FROM reference_dataset_members rdm
            JOIN reference_images ri ON ri.id = rdm.reference_image_id
            WHERE rdm.dataset_version_id = :id
        """), {"id": ds_id})
        item_count = items.scalar() or 0

        # Embeddings by model
        emb = await db.execute(text("""
            SELECT re.embedding_model_version, count(*) as cnt
            FROM reference_embeddings re
            JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
            WHERE rdm.dataset_version_id = :id
            GROUP BY re.embedding_model_version
        """), {"id": ds_id})
        emb_by_model = {r["embedding_model_version"]: r["cnt"] for r in emb.mappings()}

        datasets.append({
            **dict(row),
            "item_count": item_count,
            "region_codes": regions,
            "label_values": labels,
            "embedding_counts_by_model": emb_by_model,
        })

    return datasets


# ── Dataset Stats ───────────────────────────────────────────────────

@data_router.get("/datasets/{dataset_version}/stats")
async def dataset_stats(dataset_version: str, db: AsyncSession = Depends(get_db)):
    """Detailed stats for a single dataset."""
    ds = await db.execute(text(
        "SELECT * FROM reference_dataset_versions WHERE dataset_version = :dv"
    ), {"dv": dataset_version})
    row = ds.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ds_id = str(row["id"])

    # Splits
    splits = await db.execute(text(
        "SELECT split, count(*) as cnt FROM reference_dataset_members WHERE dataset_version_id = :id GROUP BY split"
    ), {"id": ds_id})

    # Regions
    regions = await db.execute(text("""
        SELECT ri.region_code, count(*) as cnt FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        WHERE rdm.dataset_version_id = :id GROUP BY ri.region_code ORDER BY ri.region_code
    """), {"id": ds_id})

    # Labels
    labels = await db.execute(text("""
        SELECT rit.authenticity_status, count(*) as cnt FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE rdm.dataset_version_id = :id GROUP BY rit.authenticity_status
    """), {"id": ds_id})

    # Embeddings by model
    emb = await db.execute(text("""
        SELECT re.embedding_model_version, count(*) as cnt FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        WHERE rdm.dataset_version_id = :id GROUP BY re.embedding_model_version
    """), {"id": ds_id})

    # Condition grades
    cond = await db.execute(text("""
        SELECT icm.condition_grade, count(*) as cnt FROM item_condition_metadata icm
        JOIN reference_items rit ON rit.id = icm.reference_item_id
        JOIN reference_images ri ON ri.reference_item_id = rit.id
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = ri.id
        WHERE rdm.dataset_version_id = :id AND icm.condition_grade IS NOT NULL
        GROUP BY icm.condition_grade
    """), {"id": ds_id})

    # Component statuses
    comp = await db.execute(text("""
        SELECT icc.component_status, count(*) as cnt FROM item_component_conditions icc
        JOIN item_condition_metadata icm ON icm.id = icc.item_condition_metadata_id
        JOIN reference_items rit ON rit.id = icm.reference_item_id
        JOIN reference_images ri ON ri.reference_item_id = rit.id
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = ri.id
        WHERE rdm.dataset_version_id = :id AND icc.component_status IS NOT NULL
        GROUP BY icc.component_status
    """), {"id": ds_id})

    return {
        **dict(row),
        "splits": {r["split"]: r["cnt"] for r in splits.mappings()},
        "region_counts": {r["region_code"]: r["cnt"] for r in regions.mappings()},
        "label_counts": {r["authenticity_status"]: r["cnt"] for r in labels.mappings()},
        "embedding_counts_by_model": {r["embedding_model_version"]: r["cnt"] for r in emb.mappings()},
        "condition_grades": {r["condition_grade"]: r["cnt"] for r in cond.mappings()},
        "component_statuses": {r["component_status"]: r["cnt"] for r in comp.mappings()},
    }


# ── Dataset Warnings ────────────────────────────────────────────────

@data_router.get("/datasets/{dataset_version}/warnings")
async def dataset_warnings(dataset_version: str, db: AsyncSession = Depends(get_db)):
    """Compute data quality warnings for a dataset."""
    ds = await db.execute(text(
        "SELECT id, source_type FROM reference_dataset_versions WHERE dataset_version = :dv"
    ), {"dv": dataset_version})
    row = ds.first()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ds_id = str(row[0])
    source_type = row[1]

    warnings: list[dict] = []

    # Missing embeddings
    img_count = await db.execute(text(
        "SELECT count(*) FROM reference_dataset_members WHERE dataset_version_id = :id"
    ), {"id": ds_id})
    total_images = img_count.scalar() or 0

    emb_models = await db.execute(text("""
        SELECT DISTINCT re.embedding_model_version FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        WHERE rdm.dataset_version_id = :id
    """), {"id": ds_id})
    for mr in emb_models.mappings():
        mv = mr["embedding_model_version"]
        ec = await db.execute(text("""
            SELECT count(*) FROM reference_embeddings re
            JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
            WHERE rdm.dataset_version_id = :id AND re.embedding_model_version = :mv
        """), {"id": ds_id, "mv": mv})
        emb_count = ec.scalar() or 0
        if emb_count < total_images:
            warnings.append({
                "severity": "warning",
                "type": "missing_embeddings",
                "message": f"{mv}: {emb_count}/{total_images} images have embeddings",
                "affected_count": total_images - emb_count,
                "recommended_action": f"make reembed-reference-data DATASET={dataset_version} MODEL={mv}",
            })

    # Unexpected region codes
    known = {"EXTERIOR_CANVAS", "FRONT_LOGO_PRINT", "INTERIOR_HEAT_STAMP",
             "HARDWARE_ENGRAVING", "STITCHING_DETAIL", "DATE_CODE_AREA",
             "EXTERNAL_LEATHER_TEXTURE", "EXTERNAL_FABRIC_TEXTURE"}
    reg = await db.execute(text("""
        SELECT DISTINCT ri.region_code FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id WHERE rdm.dataset_version_id = :id
    """), {"id": ds_id})
    for rr in reg.mappings():
        if rr["region_code"] not in known:
            warnings.append({
                "severity": "info",
                "type": "unexpected_region",
                "message": f"Unexpected region code: {rr['region_code']}",
                "affected_count": 1,
                "recommended_action": "Check canonical region mapping or legacy data",
            })

    # Missing label reviews
    no_review = await db.execute(text("""
        SELECT count(DISTINCT ri.reference_item_id) FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        WHERE rdm.dataset_version_id = :id
          AND ri.reference_item_id NOT IN (SELECT reference_item_id FROM reference_label_reviews)
    """), {"id": ds_id})
    missing_reviews = no_review.scalar() or 0
    if missing_reviews > 0:
        warnings.append({
            "severity": "warning",
            "type": "missing_label_review",
            "message": f"{missing_reviews} item(s) have no label review",
            "affected_count": missing_reviews,
            "recommended_action": "Add label reviews for provenance tracking",
        })

    # External dataset missing source info
    if source_type == "public_external":
        ds_full = await db.execute(text(
            "SELECT description FROM reference_dataset_versions WHERE id = :id"
        ), {"id": ds_id})
        desc = ds_full.scalar() or ""
        if not desc or len(desc) < 10:
            warnings.append({
                "severity": "info",
                "type": "missing_source_info",
                "message": "External dataset has minimal description/source metadata",
                "affected_count": 1,
                "recommended_action": "Update dataset description with source URL, license, and citation",
            })

    return warnings


# ── Dataset Images ──────────────────────────────────────────────────

@data_router.get("/datasets/{dataset_version}/images")
async def dataset_images(
    dataset_version: str,
    split: str = Query(default=""),
    region_code: str = Query(default=""),
    label: str = Query(default=""),
    quality_status: str = Query(default=""),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated image browser for a dataset."""
    ds = await db.execute(text(
        "SELECT id FROM reference_dataset_versions WHERE dataset_version = :dv"
    ), {"dv": dataset_version})
    ds_row = ds.first()
    if not ds_row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ds_id = str(ds_row[0])

    conditions = ["rdm.dataset_version_id = :id"]
    params: dict = {"id": ds_id, "limit": limit, "offset": offset}

    if split:
        conditions.append("rdm.split = :split")
        params["split"] = split
    if region_code:
        conditions.append("ri.region_code = :region")
        params["region"] = region_code
    if label:
        conditions.append("rit.authenticity_status = :label")
        params["label"] = label

    where = " AND ".join(conditions)

    result = await db.execute(text(f"""
        SELECT ri.id as reference_image_id, ri.reference_item_id, ri.region_code,
               ri.object_uri, ri.created_at, rdm.split,
               rit.authenticity_status
        FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE {where}
        ORDER BY ri.region_code, ri.created_at
        LIMIT :limit OFFSET :offset
    """), params)

    # Count
    count_result = await db.execute(text(f"""
        SELECT count(*) FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE {where}
    """), params)
    total = count_result.scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "images": [dict(r) for r in result.mappings()],
    }


# ── Dataset Items ───────────────────────────────────────────────────

@data_router.get("/datasets/{dataset_version}/items")
async def dataset_items(dataset_version: str, db: AsyncSession = Depends(get_db)):
    """Item browser for a dataset."""
    ds = await db.execute(text(
        "SELECT id FROM reference_dataset_versions WHERE dataset_version = :dv"
    ), {"dv": dataset_version})
    ds_row = ds.first()
    if not ds_row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ds_id = str(ds_row[0])

    result = await db.execute(text("""
        SELECT rit.id as reference_item_id, rit.authenticity_status, rit.brand,
               rit.category, rit.material, rit.source, rit.label_confidence,
               count(rdm.id) as image_count,
               min(rdm.split) as split
        FROM reference_items rit
        JOIN reference_images ri ON ri.reference_item_id = rit.id
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = ri.id
        WHERE rdm.dataset_version_id = :id
        GROUP BY rit.id ORDER BY rit.authenticity_status, rit.brand
    """), {"id": ds_id})
    items_raw = [dict(r) for r in result.mappings()]

    # Enrich with condition metadata
    for item in items_raw:
        cond = await db.execute(text("""
            SELECT condition_grade, known_repairs, third_party_repair
            FROM item_condition_metadata WHERE reference_item_id = :iid LIMIT 1
        """), {"iid": str(item["reference_item_id"])})
        cr = cond.mappings().first()
        item["condition_grade"] = cr["condition_grade"] if cr else None
        item["known_repairs"] = cr["known_repairs"] if cr else False
        item["third_party_repair"] = cr["third_party_repair"] if cr else False

    return items_raw


# ── Model Coverage ──────────────────────────────────────────────────

@data_router.get("/models/{model_version}/coverage")
async def model_coverage(model_version: str, db: AsyncSession = Depends(get_db)):
    """Embedding coverage for a model across datasets."""
    result = await db.execute(text("""
        SELECT rdv.dataset_version, rdv.status,
               count(DISTINCT rdm.reference_image_id) as image_count,
               count(DISTINCT re.reference_image_id) as embedding_count
        FROM reference_dataset_versions rdv
        JOIN reference_dataset_members rdm ON rdm.dataset_version_id = rdv.id
        LEFT JOIN reference_embeddings re ON re.reference_image_id = rdm.reference_image_id
            AND re.embedding_model_version = :mv
        GROUP BY rdv.id ORDER BY rdv.dataset_version
    """), {"mv": model_version})

    return [
        {
            **dict(r),
            "coverage_pct": round(r["embedding_count"] / r["image_count"] * 100, 1) if r["image_count"] > 0 else 0.0,
        }
        for r in result.mappings()
    ]
