"""Region-specific analysis utilities.

Computes per-region coverage, readiness, and embedding diagnostics for
governed datasets. Works on current datasets (smoke, lab, public external)
and prepares the framework for future real microscope/gold-set data.

Results are diagnostic only — they do not prove authentication accuracy.
"""

from __future__ import annotations

from collections import defaultdict

import psycopg2

from experiments.metrics import compute_metrics

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"

# ---------------------------------------------------------------------------
# Minimal region taxonomy registry
# ---------------------------------------------------------------------------
# Conceptual source: docs/reference/luxury-item-inspection-region-taxonomy.md
# Future: replace with a formal region registry loaded from config or DB.

REGION_METADATA: dict[str, dict] = {
    "EXTERIOR_CANVAS": {
        "inspection_layer": "exterior",
        "tier": 1,
        "capture_type": "microscope",
        "condition_sensitive": True,
        "repair_sensitive": False,
        "external_dataset_only": False,
    },
    "FRONT_LOGO_PRINT": {
        "inspection_layer": "exterior",
        "tier": 1,
        "capture_type": "microscope",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": False,
    },
    "INTERIOR_HEAT_STAMP": {
        "inspection_layer": "interior",
        "tier": 1,
        "capture_type": "microscope",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": False,
    },
    "HARDWARE_ENGRAVING": {
        "inspection_layer": "hardware",
        "tier": 1,
        "capture_type": "microscope",
        "condition_sensitive": False,
        "repair_sensitive": True,
        "external_dataset_only": False,
    },
    "STITCHING_DETAIL": {
        "inspection_layer": "construction",
        "tier": 1,
        "capture_type": "microscope",
        "condition_sensitive": True,
        "repair_sensitive": True,
        "external_dataset_only": False,
    },
    "DATE_CODE_AREA": {
        "inspection_layer": "interior",
        "tier": 1,
        "capture_type": "microscope",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": False,
    },
    "EXTERNAL_LEATHER_TEXTURE": {
        "inspection_layer": "external",
        "tier": None,
        "capture_type": "external_dataset",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": True,
    },
    "EXTERNAL_FABRIC_TEXTURE": {
        "inspection_layer": "external",
        "tier": None,
        "capture_type": "external_dataset",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": True,
    },
    "EXTERNAL_LUXURY_MACRO": {
        "inspection_layer": "external",
        "tier": None,
        "capture_type": "external_dataset",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": True,
    },
}

# Readiness thresholds
READINESS_THRESHOLDS = {
    "no_data": 0,
    "sparse": 1,
    "diagnostic_only": 10,
    "evaluation_ready": 25,
    "training_candidate": 100,
}


def compute_readiness(image_count: int) -> str:
    """Compute readiness level from image count.

    Readiness depends on label quality, item diversity, split quality, and
    provenance — image count alone is not sufficient. This is a rough proxy.
    """
    if image_count == 0:
        return "no_data"
    if image_count < READINESS_THRESHOLDS["diagnostic_only"]:
        return "sparse"
    if image_count < READINESS_THRESHOLDS["evaluation_ready"]:
        return "diagnostic_only"
    if image_count < READINESS_THRESHOLDS["training_candidate"]:
        return "evaluation_ready"
    return "training_candidate"


def get_region_meta(region_code: str) -> dict:
    """Get metadata for a region code, with unknown-region fallback."""
    if region_code in REGION_METADATA:
        return {**REGION_METADATA[region_code], "known": True}
    return {
        "inspection_layer": "unknown",
        "tier": None,
        "capture_type": "unknown",
        "condition_sensitive": False,
        "repair_sensitive": False,
        "external_dataset_only": False,
        "known": False,
    }


def is_external_region(region_code: str) -> bool:
    """Check if a region code is an external/public-dataset-only region."""
    meta = get_region_meta(region_code)
    return meta.get("external_dataset_only", False) or region_code.startswith("EXTERNAL_")


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------

def compute_region_coverage(records: list[dict]) -> list[dict]:
    """Compute per-region coverage statistics from dataset records.

    Args:
        records: List of dicts with keys: region_code, reference_image_id,
                 reference_item_id, split, authenticity_status.

    Returns:
        List of per-region coverage dicts sorted by region_code.
    """
    by_region: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_region[rec["region_code"]].append(rec)

    results = []
    for region_code in sorted(by_region.keys()):
        recs = by_region[region_code]
        image_ids = {str(r["reference_image_id"]) for r in recs}
        item_ids = {str(r["reference_item_id"]) for r in recs}
        splits = defaultdict(int)
        labels = defaultdict(int)
        for r in recs:
            splits[r.get("split", "unknown")] += 1
            labels[r.get("authenticity_status", "unknown")] += 1

        image_count = len(image_ids)
        meta = get_region_meta(region_code)

        warnings = []
        if not meta["known"]:
            warnings.append("unknown_region_code")
        if is_external_region(region_code):
            warnings.append("external_dataset_only")
        if image_count < 10:
            warnings.append("sparse_coverage")

        results.append({
            "region_code": region_code,
            "image_count": image_count,
            "item_count": len(item_ids),
            "splits": dict(sorted(splits.items())),
            "labels": dict(sorted(labels.items())),
            "readiness": compute_readiness(image_count),
            "metadata": meta,
            "warnings": warnings,
        })

    return results


def compute_embedding_coverage(
    dataset_version: str,
    model_version: str,
    region_codes: list[str] | None = None,
) -> dict[str, dict]:
    """Query DB for per-region embedding counts for a given model.

    Returns dict of region_code -> {embedded, total, coverage_pct}.
    """
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Get dataset version ID
    cur.execute(
        "SELECT id FROM reference_dataset_versions WHERE dataset_version = %s",
        (dataset_version,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {}
    ds_id = str(row[0])

    # Total images per region
    cur.execute("""
        SELECT ri.region_code, count(DISTINCT ri.id)
        FROM reference_dataset_members dm
        JOIN reference_images ri ON ri.id = dm.reference_image_id
        WHERE dm.dataset_version_id = %s
        GROUP BY ri.region_code
        ORDER BY ri.region_code
    """, (ds_id,))
    totals = {r[0]: r[1] for r in cur.fetchall()}

    # Embedded images per region for selected model
    cur.execute("""
        SELECT ri.region_code, count(DISTINCT re.reference_image_id)
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        WHERE dm.dataset_version_id = %s AND re.embedding_model_version = %s
        GROUP BY ri.region_code
        ORDER BY ri.region_code
    """, (ds_id, model_version))
    embedded = {r[0]: r[1] for r in cur.fetchall()}

    cur.close()
    conn.close()

    all_regions = sorted(set(totals.keys()) | set(embedded.keys()))
    if region_codes:
        all_regions = [r for r in all_regions if r in region_codes]

    result = {}
    for rc in all_regions:
        total = totals.get(rc, 0)
        emb = embedded.get(rc, 0)
        result[rc] = {
            "total_images": total,
            "embedded": emb,
            "missing": total - emb,
            "coverage_pct": round(emb / total * 100, 1) if total > 0 else 0.0,
        }
    return result


# ---------------------------------------------------------------------------
# Per-region embedding diagnostics
# ---------------------------------------------------------------------------

def compute_per_region_metrics(
    records: list[dict],
    embeddings_by_image: dict[str, list[float]],
    min_images: int = 2,
) -> list[dict]:
    """Compute embedding metrics per region.

    Args:
        records: Dataset records with region_code, reference_image_id,
                 authenticity_status.
        embeddings_by_image: Dict of reference_image_id -> embedding vector.
        min_images: Minimum images in a region to compute metrics.

    Returns:
        List of per-region metric dicts.
    """
    by_region: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        img_id = str(rec["reference_image_id"])
        if img_id in embeddings_by_image:
            by_region[rec["region_code"]].append({
                **rec,
                "embedding": embeddings_by_image[img_id],
            })

    results = []
    for region_code in sorted(by_region.keys()):
        recs = by_region[region_code]
        if len(recs) < min_images:
            results.append({
                "region_code": region_code,
                "embedding_count": len(recs),
                "metrics": None,
                "note": f"fewer than {min_images} embeddings — metrics skipped",
            })
            continue

        embs = [r["embedding"] for r in recs]
        labels = [r.get("authenticity_status", "unknown") for r in recs]
        regions = [r["region_code"] for r in recs]

        unique_labels = set(labels)
        metrics = compute_metrics(embs, labels, regions)

        note = ""
        if len(unique_labels) <= 1:
            note = "single-label region — same/different-label metrics are limited"

        results.append({
            "region_code": region_code,
            "embedding_count": len(recs),
            "metrics": metrics,
            "note": note,
        })

    return results


def load_embeddings_for_dataset(
    dataset_version: str,
    model_version: str,
) -> dict[str, list[float]]:
    """Load embeddings from DB for all images in a dataset/model combo.

    Returns dict of reference_image_id (str) -> embedding (list[float]).
    """
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM reference_dataset_versions WHERE dataset_version = %s",
        (dataset_version,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return {}
    ds_id = str(row[0])

    cur.execute("""
        SELECT re.reference_image_id, re.embedding
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        WHERE dm.dataset_version_id = %s AND re.embedding_model_version = %s
    """, (ds_id, model_version))

    result = {}
    for img_id, emb in cur.fetchall():
        if isinstance(emb, str):
            # pgvector text format: [0.1,0.2,...]
            emb = [float(x) for x in emb.strip("[]").split(",")]
        elif isinstance(emb, (list, tuple)):
            emb = [float(x) for x in emb]
        else:
            # numpy array or similar
            emb = list(emb)
        result[str(img_id)] = emb

    cur.close()
    conn.close()
    return result


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_coverage_table(coverage: list[dict]) -> str:
    """Format region coverage as a markdown table."""
    lines = [
        "| Region | Images | Items | Readiness | Splits | Labels | Warnings |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in coverage:
        splits_str = ", ".join(f"{k}:{v}" for k, v in c["splits"].items())
        labels_str = ", ".join(f"{k}:{v}" for k, v in c["labels"].items())
        warnings_str = ", ".join(c["warnings"]) if c["warnings"] else ""
        lines.append(
            f"| {c['region_code']} | {c['image_count']} | {c['item_count']} "
            f"| {c['readiness']} | {splits_str} | {labels_str} | {warnings_str} |"
        )
    return "\n".join(lines)


def format_metrics_table(region_metrics: list[dict]) -> str:
    """Format per-region metrics as a markdown table."""
    lines = [
        "| Region | Embeddings | Dim | Cluster sep | NN agree | R@1 | R@3 | R@5 | Same-label | Diff-label | Note |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rm in region_metrics:
        m = rm.get("metrics")
        if m is None:
            lines.append(
                f"| {rm['region_code']} | {rm['embedding_count']} | — | — | — | — | — | — | — | — | {rm.get('note', '')} |"
            )
            continue
        lines.append(
            f"| {rm['region_code']} | {rm['embedding_count']} "
            f"| {m.get('dimension', '')} "
            f"| {m.get('cluster_separation', 0):.4f} "
            f"| {m.get('nn_agreement_rate', 0):.1%} "
            f"| {m.get('recall_at_1', 0):.4f} "
            f"| {m.get('recall_at_3', 0):.4f} "
            f"| {m.get('recall_at_5', 0):.4f} "
            f"| {m.get('same_label_mean', 0):.4f} "
            f"| {m.get('diff_label_mean', 0):.4f} "
            f"| {rm.get('note', '')} |"
        )
    return "\n".join(lines)


def print_summary_table(
    coverage: list[dict],
    embedding_cov: dict[str, dict],
    region_metrics: list[dict],
) -> None:
    """Print a concise console summary table."""
    metrics_by_region = {rm["region_code"]: rm for rm in region_metrics}

    print(f"\n{'Region':<30} {'Imgs':>5} {'Items':>5} {'Splits':>8} "
          f"{'Embeds':>6} {'Ready':<20} {'NN Agree':>10} {'ClustSep':>10} {'Warnings'}")
    print("-" * 130)

    for c in coverage:
        rc = c["region_code"]
        ec = embedding_cov.get(rc, {})
        rm = metrics_by_region.get(rc, {})
        m = rm.get("metrics")

        nn = f"{m['nn_agreement_rate']:.1%}" if m else "—"
        cs = f"{m['cluster_separation']:.4f}" if m else "—"
        n_splits = len(c["splits"])
        warns = ", ".join(c["warnings"]) if c["warnings"] else ""

        print(f"{rc:<30} {c['image_count']:>5} {c['item_count']:>5} {n_splits:>8} "
              f"{ec.get('embedded', 0):>6} {c['readiness']:<20} {nn:>10} {cs:>10} {warns}")
    print()
