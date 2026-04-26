
from auth_common.database import get_db
from auth_common.logging import get_logger
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
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


# ── Helper ──────────────────────────────────────────────────────────

async def _count_embeddings(db: AsyncSession, dataset_version: str, model_version: str) -> int:
    """Count embeddings for a dataset/model pair."""
    result = await db.execute(text("""
        SELECT count(*) FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        WHERE rdv.dataset_version = :dataset AND re.embedding_model_version = :model
    """), {"dataset": dataset_version, "model": model_version})
    return result.scalar() or 0


async def _check_embeddings_or_error(
    db: AsyncSession, dataset_version: str, model_version: str, operation: str,
) -> None:
    """Raise structured 404 if no embeddings exist for the pair."""
    count = await _count_embeddings(db, dataset_version, model_version)
    if count == 0:
        raise HTTPException(status_code=404, detail={
            "error": f"No embeddings found for {operation}",
            "dataset_version": dataset_version,
            "model_version": model_version,
            "embedding_count": 0,
            "recommended_action": f"Run: make reembed-reference-data DATASET={dataset_version} MODEL={model_version}",
        })


# ── Datasets ────────────────────────────────────────────────────────

@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT rdv.id, rdv.dataset_version, rdv.status, rdv.source_type, rdv.created_at,
               count(rdm.id) as image_count,
               count(rdm.id) FILTER (WHERE rdm.split = 'train') as train_count,
               count(rdm.id) FILTER (WHERE rdm.split = 'validation') as validation_count,
               count(rdm.id) FILTER (WHERE rdm.split = 'test') as test_count
        FROM reference_dataset_versions rdv
        LEFT JOIN reference_dataset_members rdm ON rdm.dataset_version_id = rdv.id
        GROUP BY rdv.id
        ORDER BY rdv.created_at DESC
    """))
    return [dict(r) for r in result.mappings()]


@router.get("/datasets/{dataset_version}")
async def get_dataset(dataset_version: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT rdv.* FROM reference_dataset_versions rdv WHERE rdv.dataset_version = :dv
    """), {"dv": dataset_version})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    ds_id = str(row["id"])

    splits = await db.execute(text("""
        SELECT split, count(*) as cnt FROM reference_dataset_members
        WHERE dataset_version_id = :id GROUP BY split ORDER BY split
    """), {"id": ds_id})

    regions = await db.execute(text("""
        SELECT DISTINCT ri.region_code FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        WHERE rdm.dataset_version_id = :id ORDER BY ri.region_code
    """), {"id": ds_id})

    labels = await db.execute(text("""
        SELECT DISTINCT rit.authenticity_status FROM reference_dataset_members rdm
        JOIN reference_images ri ON ri.id = rdm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE rdm.dataset_version_id = :id
    """), {"id": ds_id})

    emb_models = await db.execute(text("""
        SELECT DISTINCT re.embedding_model_version FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        WHERE rdm.dataset_version_id = :id
    """), {"id": ds_id})

    return {
        **dict(row),
        "splits": {r["split"]: r["cnt"] for r in splits.mappings()},
        "region_codes": [r["region_code"] for r in regions.mappings()],
        "label_values": [r["authenticity_status"] for r in labels.mappings()],
        "embedding_models": [r["embedding_model_version"] for r in emb_models.mappings()],
    }


@router.get("/datasets/{dataset_version}/models")
async def get_dataset_models(dataset_version: str, db: AsyncSession = Depends(get_db)):
    """Return models with embedding availability for a dataset."""
    # Check dataset exists
    ds = await db.execute(text(
        "SELECT id FROM reference_dataset_versions WHERE dataset_version = :dv"
    ), {"dv": dataset_version})
    ds_row = ds.first()
    if not ds_row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    ds_id = str(ds_row[0])

    image_count_result = await db.execute(text(
        "SELECT count(*) FROM reference_dataset_members WHERE dataset_version_id = :id"
    ), {"id": ds_id})
    image_count = image_count_result.scalar() or 0

    # Get all embedding model versions that have embeddings for this dataset
    emb_result = await db.execute(text("""
        SELECT re.embedding_model_version, count(*) as embedding_count
        FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        WHERE rdm.dataset_version_id = :id
        GROUP BY re.embedding_model_version
        ORDER BY re.embedding_model_version
    """), {"id": ds_id})
    emb_rows = {r["embedding_model_version"]: r["embedding_count"] for r in emb_result.mappings()}

    # Also get registered model_versions to include models without embeddings
    mv_result = await db.execute(text("SELECT model_name, model_version FROM model_versions"))
    registered = {r["model_version"]: r["model_name"] for r in mv_result.mappings()}

    # Merge: all embedding model versions + all registered model versions
    all_versions = set(emb_rows.keys()) | set(registered.keys())

    models = []
    for mv in sorted(all_versions):
        ec = emb_rows.get(mv, 0)
        models.append({
            "model_name": registered.get(mv, mv.split("_")[0] if "_" in mv else mv),
            "model_version": mv,
            "embedding_count": ec,
            "image_count": image_count,
            "compatible": ec > 0,
        })

    return models


# ── Models ──────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """Return all known embedding model versions (registered + in-use)."""
    # Registered models
    registered = await db.execute(text("SELECT * FROM model_versions ORDER BY created_at DESC"))
    reg_rows = [dict(r) for r in registered.mappings()]
    reg_versions = {r["model_version"] for r in reg_rows}

    # Embedding model versions actually in use (may not be in model_versions table)
    in_use = await db.execute(text("""
        SELECT DISTINCT embedding_model_version FROM reference_embeddings
    """))
    for r in in_use.mappings():
        mv = r["embedding_model_version"]
        if mv not in reg_versions:
            reg_rows.append({
                "id": None,
                "model_name": mv,
                "model_version": mv,
                "model_type": "EMBEDDING",
                "artifact_uri": None,
                "description": "Hand-crafted baseline (not a trained model artifact)",
                "is_active": True,
                "created_at": None,
            })

    return reg_rows


# ── Compatibility ───────────────────────────────────────────────────

@router.get("/compatibility")
async def get_compatibility(db: AsyncSession = Depends(get_db)):
    """Return compatibility matrix: which dataset/model pairs have embeddings."""
    result = await db.execute(text("""
        SELECT rdv.dataset_version,
               re.embedding_model_version as model_version,
               count(*) as embedding_count,
               count(*) FILTER (WHERE rdm.split = 'train') as train_count,
               count(*) FILTER (WHERE rdm.split = 'validation') as validation_count,
               count(*) FILTER (WHERE rdm.split = 'test') as test_count,
               count(DISTINCT rdm.reference_image_id) as image_count
        FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        GROUP BY rdv.dataset_version, re.embedding_model_version
        ORDER BY rdv.dataset_version, re.embedding_model_version
    """))
    rows = result.mappings().all()

    return [
        {
            **dict(r),
            "has_embeddings": r["embedding_count"] > 0,
            "has_test_items": r["test_count"] > 0,
            "ready_for_analysis": r["embedding_count"] >= 2,
            "ready_for_projection": r["embedding_count"] >= 2,
            "ready_for_neighbors": r["test_count"] > 0 and r["train_count"] > 0,
        }
        for r in rows
    ]


# ── Evaluations ─────────────────────────────────────────────────────

@router.get("/evaluations")
async def list_evaluations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text(
        "SELECT * FROM evaluation_runs ORDER BY started_at DESC LIMIT 50"
    ))
    return [dict(r) for r in result.mappings()]


@router.get("/evaluations/{evaluation_run_id}")
async def get_evaluation(evaluation_run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(text(
        "SELECT * FROM evaluation_runs WHERE id = :id"
    ), {"id": evaluation_run_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    items = await db.execute(text("""
        SELECT * FROM evaluation_items WHERE evaluation_run_id = :id ORDER BY region_code, result
    """), {"id": evaluation_run_id})

    return {**dict(row), "items": [dict(i) for i in items.mappings()]}


# ── Projections ─────────────────────────────────────────────────────

@router.get("/projections")
async def get_projections(
    dataset_version: str = Query(...),
    model_version: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Return 2D PCA projection points computed from reference embeddings."""
    import numpy as np

    await _check_embeddings_or_error(db, dataset_version, model_version, "projection")

    result = await db.execute(text("""
        SELECT re.reference_image_id, re.embedding, rit.authenticity_status,
               ri.region_code, COALESCE(rdm.split, 'unknown') as split
        FROM reference_embeddings re
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        LEFT JOIN reference_dataset_members rdm ON rdm.reference_image_id = ri.id
        LEFT JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        WHERE re.embedding_model_version = :model
          AND (rdv.dataset_version = :dataset OR rdv.id IS NULL)
        ORDER BY ri.id
    """), {"model": model_version, "dataset": dataset_version})
    rows = result.mappings().all()

    if len(rows) < 2:
        return []

    ids = [str(r["reference_image_id"]) for r in rows]
    labels = [r["authenticity_status"] for r in rows]
    regions = [r["region_code"] for r in rows]
    splits = [r["split"] for r in rows]

    embeddings = []
    for r in rows:
        vec = r["embedding"]
        if isinstance(vec, str):
            vec = [float(x) for x in vec.strip("[]").split(",")]
        embeddings.append(vec)

    matrix = np.array(embeddings, dtype=float)
    centered = matrix - matrix.mean(axis=0)
    cov = np.cov(centered.T)
    _eigenvalues, eigenvectors = np.linalg.eigh(cov)
    top2 = eigenvectors[:, -2:][:, ::-1]
    projected = centered @ top2

    return [
        {
            "reference_image_id": ids[i],
            "x": round(float(projected[i, 0]), 6),
            "y": round(float(projected[i, 1]), 6),
            "label": labels[i],
            "region_code": regions[i],
            "split": splits[i],
        }
        for i in range(len(ids))
    ]


# ── Neighbors ───────────────────────────────────────────────────────

@router.get("/neighbors")
async def get_neighbors(
    dataset_version: str = Query(...),
    model_version: str = Query(...),
    k: int = Query(default=5),
    db: AsyncSession = Depends(get_db),
):
    """Compute nearest neighbors for test-split images."""
    import numpy as np

    await _check_embeddings_or_error(db, dataset_version, model_version, "neighbor inspection")

    test_result = await db.execute(text("""
        SELECT re.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = :model AND rdv.dataset_version = :dataset
          AND rdm.include_in_evaluation = TRUE
        ORDER BY ri.region_code
    """), {"model": model_version, "dataset": dataset_version})
    test_rows = test_result.mappings().all()

    search_result = await db.execute(text("""
        SELECT re.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = :model AND rdv.dataset_version = :dataset
          AND rdm.include_in_search = TRUE
    """), {"model": model_version, "dataset": dataset_version})
    search_rows = search_result.mappings().all()

    def parse_vec(v):
        if isinstance(v, str):
            return np.array([float(x) for x in v.strip("[]").split(",")], dtype=float)
        return np.array(v, dtype=float)

    def cosine_sim(a, b):
        d = np.dot(a, b)
        n = np.linalg.norm(a) * np.linalg.norm(b)
        return float(d / n) if n > 0 else 0.0

    items = []
    nn_agree = 0
    total = 0

    for t in test_rows:
        t_emb = parse_vec(t["embedding"])
        t_region = t["region_code"]
        t_id = str(t["reference_image_id"])

        sims = []
        for s in search_rows:
            s_id = str(s["reference_image_id"])
            if s_id == t_id or s["region_code"] != t_region:
                continue
            sim = cosine_sim(t_emb, parse_vec(s["embedding"]))
            sims.append({"id": s_id, "label": s["authenticity_status"], "similarity": round(sim, 4)})

        sims.sort(key=lambda x: x["similarity"], reverse=True)
        top = sims[:k]
        agrees = top[0]["label"] == t["authenticity_status"] if top else False
        if agrees:
            nn_agree += 1
        total += 1

        items.append({
            "reference_image_id": t_id,
            "expected_label": t["authenticity_status"],
            "region_code": t_region,
            "nn_agrees": agrees,
            "neighbors": top,
        })

    return {
        "dataset_version": dataset_version,
        "model_version": model_version,
        "k": k,
        "total": total,
        "nn_agreement": nn_agree,
        "nn_agreement_rate": round(nn_agree / total, 4) if total > 0 else 0.0,
        "items": items,
        "note": None if test_rows else "No test-split items with embeddings found. Check that evaluation-eligible images have embeddings for this model.",
    }


# ── Embedding Analysis ──────────────────────────────────────────────

@router.get("/embedding-analysis")
async def analyze_embeddings_endpoint(
    dataset_version: str = Query(...),
    model_version: str = Query(...),
    include_out_of_dataset: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Compute embedding distribution statistics.

    By default, only includes embeddings for images that are members of the
    selected dataset. Set include_out_of_dataset=true to also include
    embeddings for images with matching model_version but no dataset membership.
    """
    import numpy as np

    await _check_embeddings_or_error(db, dataset_version, model_version, "embedding analysis")

    if include_out_of_dataset:
        query = text("""
            SELECT re.embedding, rit.authenticity_status, ri.region_code
            FROM reference_embeddings re
            JOIN reference_images ri ON ri.id = re.reference_image_id
            JOIN reference_items rit ON rit.id = ri.reference_item_id
            LEFT JOIN reference_dataset_members rdm ON rdm.reference_image_id = ri.id
            LEFT JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
            WHERE re.embedding_model_version = :model
              AND (rdv.dataset_version = :dataset OR rdv.id IS NULL)
        """)
    else:
        query = text("""
            SELECT re.embedding, rit.authenticity_status, ri.region_code
            FROM reference_embeddings re
            JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
            JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
            JOIN reference_images ri ON ri.id = re.reference_image_id
            JOIN reference_items rit ON rit.id = ri.reference_item_id
            WHERE re.embedding_model_version = :model
              AND rdv.dataset_version = :dataset
        """)

    result = await db.execute(query, {"model": model_version, "dataset": dataset_version})
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail={
            "error": "No embeddings found for embedding analysis",
            "dataset_version": dataset_version,
            "model_version": model_version,
            "embedding_count": 0,
            "dataset_scoped": not include_out_of_dataset,
            "recommended_action": f"Run: make reembed-reference-data DATASET={dataset_version} MODEL={model_version}",
        })

    def parse_vec(v):
        if isinstance(v, str):
            return np.array([float(x) for x in v.strip("[]").split(",")], dtype=float)
        return np.array(v, dtype=float)

    embeddings = [parse_vec(r["embedding"]) for r in rows]
    labels = [r["authenticity_status"] for r in rows]
    regions = [r["region_code"] for r in rows]
    matrix = np.array(embeddings)
    norms = np.linalg.norm(matrix, axis=1)

    n = len(embeddings)
    max_pairs = 5000
    all_sims: list[float] = []
    same_label_sims: list[float] = []
    diff_label_sims: list[float] = []

    pairs_checked = 0
    for i in range(n):
        for j in range(i + 1, n):
            if pairs_checked >= max_pairs:
                break
            d = float(np.dot(embeddings[i], embeddings[j]))
            na = float(np.linalg.norm(embeddings[i]))
            nb = float(np.linalg.norm(embeddings[j]))
            sim = d / (na * nb) if na > 0 and nb > 0 else 0.0
            all_sims.append(sim)
            if labels[i] == labels[j]:
                same_label_sims.append(sim)
            else:
                diff_label_sims.append(sim)
            pairs_checked += 1
        if pairs_checked >= max_pairs:
            break

    intra = float(np.mean(same_label_sims)) if same_label_sims else 0.0
    inter = float(np.mean(diff_label_sims)) if diff_label_sims else 0.0

    unique_regions = sorted(set(regions))
    region_counts = {r: {"total": 0} for r in unique_regions}
    for r in regions:
        region_counts[r]["total"] += 1

    return {
        "dataset_version": dataset_version,
        "model_version": model_version,
        "dataset_scoped": not include_out_of_dataset,
        "count": n,
        "dimension": int(matrix.shape[1]) if n > 0 else 0,
        "norm_mean": round(float(norms.mean()), 4),
        "norm_min": round(float(norms.min()), 4),
        "norm_max": round(float(norms.max()), 4),
        "pairwise_mean": round(float(np.mean(all_sims)), 4) if all_sims else 0.0,
        "pairwise_min": round(float(np.min(all_sims)), 4) if all_sims else 0.0,
        "pairwise_max": round(float(np.max(all_sims)), 4) if all_sims else 0.0,
        "intra_class_mean": round(intra, 4),
        "inter_class_mean": round(inter, 4),
        "cluster_separation": round(intra - inter, 4),
        "pairs_sampled": pairs_checked,
        "region_counts": region_counts,
        "unique_labels": sorted(set(labels)),
    }


# ── Query Image ─────────────────────────────────────────────────────

@router.post("/diagnostics/query-image")
async def query_image(
    file: UploadFile,
    dataset_version: str = Form(...),
    model_version: str = Form(...),
    k: int = Form(default=5),
    include_projection: bool = Form(default=True),
    allow_low_quality: bool = Form(default=False),
    region_code: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single image and see nearest neighbors in the selected dataset/model.

    Diagnostic only — does not add the image to any dataset or reference library.
    """
    import math
    import uuid

    import numpy as np
    from auth_common.imaging import (
        compute_quality_metrics,
        compute_texture_embedding,
        compute_texture_embedding_v2,
        normalize_image,
        validate_image,
    )

    # Validate dataset/model compatibility
    emb_count = await _count_embeddings(db, dataset_version, model_version)
    if emb_count == 0:
        raise HTTPException(status_code=400, detail={
            "error": "No embeddings for this dataset/model pair",
            "dataset_version": dataset_version,
            "model_version": model_version,
            "recommended_action": f"Run: make reembed-reference-data DATASET={dataset_version} MODEL={model_version}",
        })

    # Read and validate image
    content = await file.read()
    validation = validate_image(content)
    if not validation.get("valid", False):
        raise HTTPException(status_code=400, detail={
            "error": "Invalid image",
            "issues": validation.get("issues", []),
        })

    # Quality metrics
    quality = compute_quality_metrics(content)

    if quality["quality_status"] == "FAIL" and not allow_low_quality:
        return {
            "query_id": str(uuid.uuid4()),
            "dataset_version": dataset_version,
            "model_version": model_version,
            "quality": quality,
            "embedding": None,
            "neighbors": [],
            "projection": None,
            "warnings": [
                "Query image failed quality checks.",
                "Set allow_low_quality=true to proceed anyway.",
                "Diagnostic only; not an authentication decision.",
            ],
        }

    # Normalize and embed
    norm_bytes = normalize_image(content)

    if model_version == "texture_baseline_v0.2.0":
        embedding = compute_texture_embedding_v2(norm_bytes, dim=256)
    elif "texture_baseline" in model_version:
        embedding = compute_texture_embedding(norm_bytes, dim=128)
    else:
        # Try learned model
        try:
            import io
            import sys

            import torch

            sys.path.insert(0, "/app/ml")
            from metric_learning.model import EmbeddingModel
            from metric_learning.transforms import preprocess_for_inference

            mv_row = await db.execute(text(
                "SELECT artifact_uri FROM model_versions WHERE model_version = :mv AND is_active = TRUE"
            ), {"mv": model_version})
            artifact = mv_row.scalar_one_or_none()
            if not artifact:
                raise HTTPException(status_code=400, detail={
                    "error": f"No active model artifact for {model_version}",
                    "recommended_action": "Use texture_baseline_v0.1.0 or train and register a model.",
                })

            from auth_common.s3 import download_file
            parts = artifact.replace("s3://", "").split("/", 1)
            model_bytes = download_file(parts[0], parts[1])
            m = EmbeddingModel(embedding_dim=128)
            m.load_state_dict(torch.load(io.BytesIO(model_bytes), weights_only=True, map_location="cpu"))
            m.eval()
            tensor = preprocess_for_inference(norm_bytes, input_size=224)
            with torch.no_grad():
                embedding = m(tensor).squeeze().tolist()
        except ImportError:
            embedding = compute_texture_embedding_v2(norm_bytes, dim=256) if model_version == "texture_baseline_v0.2.0" else compute_texture_embedding(norm_bytes, dim=128)

    emb_norm = float(math.sqrt(sum(x * x for x in embedding)))

    # Parse helper
    def parse_vec(v):
        if isinstance(v, str):
            return np.array([float(x) for x in v.strip("[]").split(",")], dtype=float)
        return np.array(v, dtype=float)

    def cosine_sim(a, b):
        d = float(np.dot(a, b))
        na = float(np.linalg.norm(a))
        nb = float(np.linalg.norm(b))
        return d / (na * nb) if na > 0 and nb > 0 else 0.0

    query_emb = np.array(embedding, dtype=float)

    # Resolve region filtering
    query_region = region_code.strip() if region_code and region_code.strip().upper() != "ALL" else None

    # Get available regions for this dataset/model
    avail_regions_result = await db.execute(text("""
        SELECT DISTINCT ri.region_code FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        WHERE re.embedding_model_version = :model AND rdv.dataset_version = :dataset
        ORDER BY ri.region_code
    """), {"model": model_version, "dataset": dataset_version})
    available_regions = [r["region_code"] for r in avail_regions_result.mappings()]

    if query_region and query_region not in available_regions:
        raise HTTPException(status_code=400, detail={
            "error": f"Region '{query_region}' not found in dataset",
            "available_region_codes": available_regions,
            "dataset_version": dataset_version,
        })

    # Load reference embeddings (all regions for projection, filtered for scoring)
    ref_result = await db.execute(text("""
        SELECT re.reference_image_id, re.embedding, ri.region_code,
               ri.reference_item_id, rit.authenticity_status,
               COALESCE(rdm.split, 'unknown') as split
        FROM reference_embeddings re
        JOIN reference_dataset_members rdm ON rdm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = rdm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = :model AND rdv.dataset_version = :dataset
    """), {"model": model_version, "dataset": dataset_version})
    all_ref_rows = ref_result.mappings().all()

    # Filter for scoring (region-filtered or all)
    score_rows = [r for r in all_ref_rows if r["region_code"] == query_region] if query_region else list(all_ref_rows)

    # Compute similarities
    scored = []
    for r in score_rows:
        ref_emb = parse_vec(r["embedding"])
        sim = cosine_sim(query_emb, ref_emb)
        scored.append({
            "reference_image_id": str(r["reference_image_id"]),
            "reference_item_id": str(r["reference_item_id"]),
            "region_code": r["region_code"],
            "label": r["authenticity_status"],
            "split": r["split"],
            "similarity": round(sim, 4),
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top_k = scored[:k]
    neighbors = [
        {
            "rank": i + 1,
            "reference_image_id": n["reference_image_id"],
            "reference_item_id": n["reference_item_id"],
            "region_code": n["region_code"],
            "label": n["label"],
            "split": n["split"],
            "similarity": n["similarity"],
        }
        for i, n in enumerate(top_k)
    ]

    # Projection (always uses all regions for spatial context)
    projection = None
    if include_projection and len(all_ref_rows) >= 2:
        all_embs = [parse_vec(r["embedding"]) for r in all_ref_rows]
        all_embs.append(query_emb)
        matrix = np.array(all_embs, dtype=float)
        centered = matrix - matrix.mean(axis=0)
        cov = np.cov(centered.T)
        _eigenvalues, eigenvectors = np.linalg.eigh(cov)
        top2 = eigenvectors[:, -2:][:, ::-1]
        projected = centered @ top2

        ref_points = [
            {
                "reference_image_id": str(all_ref_rows[i]["reference_image_id"]),
                "x": round(float(projected[i, 0]), 6),
                "y": round(float(projected[i, 1]), 6),
                "label": all_ref_rows[i]["authenticity_status"],
                "region_code": all_ref_rows[i]["region_code"],
                "split": all_ref_rows[i]["split"],
            }
            for i in range(len(all_ref_rows))
        ]

        query_proj = projected[-1]
        projection = {
            "query_point": {
                "x": round(float(query_proj[0]), 6),
                "y": round(float(query_proj[1]), 6),
                "label": "QUERY_IMAGE",
            },
            "reference_points": ref_points,
        }

    search_scope = "region_filtered" if query_region else "all_regions"
    warnings = ["Diagnostic only; not an authentication decision."]
    if quality["quality_status"] == "FAIL":
        warnings.insert(0, "Image failed quality checks; results may be unreliable.")

    return {
        "query_id": str(uuid.uuid4()),
        "dataset_version": dataset_version,
        "model_version": model_version,
        "query_region_code": query_region,
        "search_scope": search_scope,
        "available_region_codes": available_regions,
        "quality": quality,
        "embedding": {
            "dimension": len(embedding),
            "norm": round(emb_norm, 4),
        },
        "neighbors": neighbors,
        "projection": projection,
        "warnings": warnings,
    }
