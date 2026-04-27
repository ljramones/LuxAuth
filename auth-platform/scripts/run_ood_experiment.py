#!/usr/bin/env python3
"""Run OOD (out-of-distribution) scoring experiment.

Uses one dataset as the in-distribution reference and another as OOD queries.
Compares multiple scoring methods to distinguish ID from OOD samples.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/run_ood_experiment.py --in-dataset external_fabricnet_v0.1.0 --out-dataset external_leadata_v0.1.0
  python scripts/run_ood_experiment.py --in-dataset external_leadata_v0.1.0 --out-dataset external_fabricnet_v0.1.0 --limit 50
"""

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from experiments.ood import (
    compute_auroc,
    find_best_threshold,
    score_query,
    threshold_sweep,
)
from experiments.region_analysis import load_embeddings_for_dataset

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def load_split_embeddings(dataset_version: str, model_version: str, split: str) -> list[list[float]]:
    """Load embeddings for a specific split of a dataset."""
    import psycopg2

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    cur.execute("SELECT id FROM reference_dataset_versions WHERE dataset_version = %s", (dataset_version,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return []
    ds_id = str(row[0])

    split_clause = ""
    params: list = [ds_id, model_version]
    if split != "all":
        split_clause = "AND dm.split = %s"
        params.append(split)

    cur.execute(f"""
        SELECT re.embedding
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        WHERE dm.dataset_version_id = %s AND re.embedding_model_version = %s {split_clause}
        ORDER BY re.reference_image_id
    """, params)

    embeddings = []
    for (emb,) in cur.fetchall():
        if isinstance(emb, str):
            emb = [float(x) for x in emb.strip("[]").split(",")]
        elif isinstance(emb, (list, tuple)):
            emb = [float(x) for x in emb]
        else:
            emb = list(emb)
        embeddings.append(emb)

    cur.close()
    conn.close()
    return embeddings


def main():
    parser = argparse.ArgumentParser(description="Run OOD scoring experiment")
    parser.add_argument("--in-dataset", required=True, help="In-distribution dataset version")
    parser.add_argument("--out-dataset", required=True, help="OOD dataset version")
    parser.add_argument("--model", default="texture_baseline_v0.2.0", help="Embedding model version")
    parser.add_argument("--k", type=int, default=5, help="K for kNN-based methods")
    parser.add_argument("--split", default="test", help="Split for query images (default: test)")
    parser.add_argument("--ref-splits", default="train,validation", help="Splits for reference (default: train,validation)")
    parser.add_argument("--limit", type=int, default=None, help="Limit queries per dataset")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--notes", default="", help="Free-form notes")
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir) if args.output_dir
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "ood"
    )

    print(f"In-distribution: {args.in_dataset}")
    print(f"OOD:             {args.out_dataset}")
    print(f"Model:           {args.model}")
    print(f"K:               {args.k}")
    print(f"Query split:     {args.split}")
    print(f"Ref splits:      {args.ref_splits}")
    if args.limit:
        print(f"Limit:           {args.limit}")
    print(f"Output:          {output_dir}")

    # Load reference embeddings (in-dataset train+validation)
    print("\nLoading reference embeddings...")
    ref_embeddings = []
    for ref_split in args.ref_splits.split(","):
        ref_split = ref_split.strip()
        embs = load_split_embeddings(args.in_dataset, args.model, ref_split)
        ref_embeddings.extend(embs)
        print(f"  {ref_split}: {len(embs)} embeddings")

    if not ref_embeddings:
        # Fall back to all splits
        print("  No split-specific embeddings found, loading all...")
        all_embs = load_embeddings_for_dataset(args.in_dataset, args.model)
        ref_embeddings = list(all_embs.values())
        print(f"  all: {len(ref_embeddings)} embeddings")

    if not ref_embeddings:
        print("ERROR: No reference embeddings found.")
        sys.exit(1)

    ref_matrix = np.array(ref_embeddings, dtype=float)
    print(f"  Reference matrix: {ref_matrix.shape}")

    # Load in-distribution query embeddings (test split)
    print("\nLoading ID query embeddings...")
    id_embeddings = load_split_embeddings(args.in_dataset, args.model, args.split)
    if not id_embeddings:
        # Fall back: use a sample from all embeddings
        all_embs = load_embeddings_for_dataset(args.in_dataset, args.model)
        id_embeddings = list(all_embs.values())
    if args.limit:
        id_embeddings = id_embeddings[:args.limit]
    print(f"  ID queries: {len(id_embeddings)}")

    # Load OOD query embeddings
    print("Loading OOD query embeddings...")
    ood_embeddings = load_split_embeddings(args.out_dataset, args.model, args.split)
    if not ood_embeddings:
        all_embs = load_embeddings_for_dataset(args.out_dataset, args.model)
        ood_embeddings = list(all_embs.values())
    if args.limit:
        ood_embeddings = ood_embeddings[:args.limit]
    print(f"  OOD queries: {len(ood_embeddings)}")

    if not id_embeddings or not ood_embeddings:
        print("ERROR: Need both ID and OOD query embeddings.")
        sys.exit(1)

    # Score all queries
    print("\nScoring queries...")
    t0 = time.monotonic()

    methods = ["max_similarity", "mean_topk", "similarity_gap", "knn_density", "mahalanobis", "lof"]
    id_scores_by_method: dict[str, list[float]] = {m: [] for m in methods}
    ood_scores_by_method: dict[str, list[float]] = {m: [] for m in methods}
    all_query_results = []

    total = len(id_embeddings) + len(ood_embeddings)
    for i, emb in enumerate(id_embeddings):
        scores = score_query(np.array(emb, dtype=float), ref_matrix, k=args.k)
        for m in methods:
            id_scores_by_method[m].append(scores[m]["ood_score"])
        all_query_results.append({"type": "ID", "index": i, "scores": scores})
        if (i + 1) % 50 == 0:
            print(f"  ID [{i + 1}/{len(id_embeddings)}]")

    for i, emb in enumerate(ood_embeddings):
        scores = score_query(np.array(emb, dtype=float), ref_matrix, k=args.k)
        for m in methods:
            ood_scores_by_method[m].append(scores[m]["ood_score"])
        all_query_results.append({"type": "OOD", "index": i, "scores": scores})
        if (i + 1) % 50 == 0:
            print(f"  OOD [{i + 1}/{len(ood_embeddings)}]")

    elapsed = time.monotonic() - t0
    print(f"  Scored {total} queries in {elapsed:.1f}s")

    # Compute summary metrics per method
    print("\nComputing summary metrics...")
    method_summaries = {}
    for m in methods:
        id_s = id_scores_by_method[m]
        ood_s = ood_scores_by_method[m]

        auroc = compute_auroc(id_s, ood_s)
        id_mean = float(np.mean(id_s))
        ood_mean = float(np.mean(ood_s))
        id_std = float(np.std(id_s))
        ood_std = float(np.std(ood_s))

        # Overlap: fraction of ID scores that fall within OOD range and vice versa
        ood_min, ood_max = min(ood_s), max(ood_s)
        id_min, id_max = min(id_s), max(id_s)
        overlap_lo = max(id_min, ood_min)
        overlap_hi = min(id_max, ood_max)
        if overlap_hi > overlap_lo:
            id_in_overlap = sum(1 for s in id_s if overlap_lo <= s <= overlap_hi) / len(id_s)
            ood_in_overlap = sum(1 for s in ood_s if overlap_lo <= s <= overlap_hi) / len(ood_s)
            overlap = (id_in_overlap + ood_in_overlap) / 2
        else:
            overlap = 0.0

        sweep = threshold_sweep(id_s, ood_s)
        best = find_best_threshold(sweep)

        method_summaries[m] = {
            "auroc": round(auroc, 4),
            "id_mean": round(id_mean, 4),
            "id_std": round(id_std, 4),
            "ood_mean": round(ood_mean, 4),
            "ood_std": round(ood_std, 4),
            "separation": round(ood_mean - id_mean, 4),
            "overlap": round(overlap, 4),
            "best_threshold": best["threshold"],
            "best_false_ood_rate": best["false_ood_rate"],
            "best_missed_ood_rate": best["missed_ood_rate"],
        }

    # Print comparison
    print(f"\n{'Method':<18} {'AUROC':>7} {'ID mean':>8} {'OOD mean':>9} {'Sep':>7} "
          f"{'Overlap':>8} {'Thresh':>8} {'FalseOOD':>9} {'MissOOD':>8}")
    print("-" * 100)
    for m in methods:
        s = method_summaries[m]
        print(f"{m:<18} {s['auroc']:>7.4f} {s['id_mean']:>8.4f} {s['ood_mean']:>9.4f} "
              f"{s['separation']:>7.4f} {s['overlap']:>8.4f} {s['best_threshold']:>8.4f} "
              f"{s['best_false_ood_rate']:>9.4f} {s['best_missed_ood_rate']:>8.4f}")

    best_method = max(methods, key=lambda m: method_summaries[m]["auroc"])
    print(f"\nBest by AUROC: {best_method} ({method_summaries[best_method]['auroc']:.4f})")

    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    in_tag = args.in_dataset.replace(".", "_")
    out_tag = args.out_dataset.replace(".", "_")
    prefix = f"{in_tag}__vs__{out_tag}"

    # Summary JSON
    summary = {
        "in_dataset": args.in_dataset,
        "out_dataset": args.out_dataset,
        "model": args.model,
        "k": args.k,
        "query_split": args.split,
        "ref_splits": args.ref_splits,
        "id_count": len(id_embeddings),
        "ood_count": len(ood_embeddings),
        "ref_count": len(ref_embeddings),
        "timestamp": now.isoformat(),
        "runtime_seconds": round(elapsed, 2),
        "method_summaries": method_summaries,
        "best_method": best_method,
        "notes": args.notes,
    }
    json_path = output_dir / f"{prefix}__ood_summary.json"
    json_path.write_text(json.dumps(summary, indent=2))

    # Per-query CSV
    csv_path = output_dir / f"{prefix}__ood_scores.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["type", "index"] + [f"{m}_ood_score" for m in methods]
        writer.writerow(header)
        for qr in all_query_results:
            row = [qr["type"], qr["index"]]
            for m in methods:
                row.append(round(qr["scores"][m]["ood_score"], 6))
            writer.writerow(row)

    # Markdown report
    report_lines = [
        "# OOD Experiment Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> Results are diagnostic only. They do not prove authentication accuracy.",
        "> Public datasets are not luxury authentication datasets.",
        "",
        "## Configuration",
        "",
        f"- **In-distribution:** `{args.in_dataset}`",
        f"- **OOD:** `{args.out_dataset}`",
        f"- **Model:** `{args.model}`",
        f"- **K:** {args.k}",
        f"- **ID queries:** {len(id_embeddings)}",
        f"- **OOD queries:** {len(ood_embeddings)}",
        f"- **References:** {len(ref_embeddings)}",
        f"- **Runtime:** {elapsed:.1f}s",
        "",
        "## Method Comparison",
        "",
        "| Method | AUROC | ID mean | OOD mean | Separation | Overlap | Threshold | False OOD | Missed OOD |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m in methods:
        s = method_summaries[m]
        best_marker = " **" if m == best_method else ""
        report_lines.append(
            f"| {m}{best_marker} | {s['auroc']:.4f} | {s['id_mean']:.4f} | {s['ood_mean']:.4f} "
            f"| {s['separation']:.4f} | {s['overlap']:.4f} | {s['best_threshold']:.4f} "
            f"| {s['best_false_ood_rate']:.4f} | {s['best_missed_ood_rate']:.4f} |"
        )
    report_lines.extend([
        "",
        f"**Best method by AUROC:** {best_method} ({method_summaries[best_method]['auroc']:.4f})",
        "",
        "## Limitations",
        "",
        "- Public texture datasets, not luxury authentication datasets.",
        "- ID/OOD distinction is between dataset domains, not authentic/counterfeit.",
        "- Results are diagnostic only.",
        "",
    ])
    md_path = output_dir / f"{prefix}__ood_report.md"
    md_path.write_text("\n".join(report_lines) + "\n")

    print(f"\nSummary: {json_path}")
    print(f"Scores:  {csv_path}")
    print(f"Report:  {md_path}")


if __name__ == "__main__":
    main()
