#!/usr/bin/env python3
"""Compare region analysis results across datasets or models.

Reads generated region_analysis.json files and prints comparison summaries.
Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/compare_region_analysis.py
  python scripts/compare_region_analysis.py --dataset external_fabricnet_v0.1.0
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Compare region analysis results")
    parser.add_argument("--dataset", default=None, help="Filter by dataset version")
    parser.add_argument("--latest-for-dataset", default=None, help="Show only latest run for this dataset")
    parser.add_argument("--reports", default=None, help="Path to reports directory")
    args = parser.parse_args()

    reports_dir = (
        Path(args.reports) if args.reports
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "region-analysis"
    )

    if not reports_dir.exists():
        print(f"No region analyses found at {reports_dir}")
        sys.exit(0)

    # Load all analysis files
    all_runs = []
    for f in sorted(reports_dir.glob("*__region_analysis.json")):
        data = json.loads(f.read_text())
        if args.dataset and data.get("dataset_version") != args.dataset:
            continue
        if args.latest_for_dataset and data.get("dataset_version") != args.latest_for_dataset:
            continue
        all_runs.append(data)

    if not all_runs:
        print("No matching region analysis results found.")
        sys.exit(0)

    # Group by dataset
    datasets = sorted(set(r["dataset_version"] for r in all_runs))

    for ds in datasets:
        ds_runs = [r for r in all_runs if r["dataset_version"] == ds]
        latest = max(ds_runs, key=lambda r: r.get("timestamp", ""))

        print(f"\n{'=' * 110}")
        print(f"  Dataset: {ds}")
        print(f"  Model:   {latest['model_version']}")
        print(f"  Records: {latest['total_records']}  Embeddings: {latest['total_embeddings']}")
        print(f"{'=' * 110}")

        # Coverage summary
        coverage = latest.get("coverage", [])
        print(f"\n  {'Region':<30} {'Images':>6} {'Items':>6} {'Readiness':<20} {'Warnings'}")
        print(f"  {'-' * 100}")
        for c in coverage:
            warns = ", ".join(c.get("warnings", [])) or ""
            print(f"  {c['region_code']:<30} {c['image_count']:>6} {c['item_count']:>6} "
                  f"{c['readiness']:<20} {warns}")

        # Metrics summary
        region_metrics = latest.get("region_metrics", [])
        metrics_with_data = [rm for rm in region_metrics if rm.get("metrics")]

        if metrics_with_data:
            print(f"\n  {'Region':<30} {'Embeds':>6} {'ClustSep':>10} {'NN Agree':>10} "
                  f"{'R@1':>8} {'Note'}")
            print(f"  {'-' * 100}")
            for rm in metrics_with_data:
                m = rm["metrics"]
                print(f"  {rm['region_code']:<30} {rm['embedding_count']:>6} "
                      f"{m.get('cluster_separation', 0):>10.4f} "
                      f"{m.get('nn_agreement_rate', 0):>9.1%} "
                      f"{m.get('recall_at_1', 0):>8.4f} "
                      f"{rm.get('note', '')[:40]}")

        # Highlights
        if metrics_with_data:
            best_cs = max(metrics_with_data, key=lambda r: r["metrics"].get("cluster_separation", 0))
            worst_cs = min(metrics_with_data, key=lambda r: r["metrics"].get("cluster_separation", 0))
            print("\n  Highlights (diagnostic only):")
            print(f"    Best cluster sep:  {best_cs['region_code']} "
                  f"({best_cs['metrics']['cluster_separation']:.4f})")
            print(f"    Worst cluster sep: {worst_cs['region_code']} "
                  f"({worst_cs['metrics']['cluster_separation']:.4f})")

        # Sparsest regions
        sparse = [c for c in coverage if c["readiness"] in ("no_data", "sparse")]
        if sparse:
            print("\n  Sparse/missing regions:")
            for c in sparse:
                print(f"    {c['region_code']}: {c['image_count']} images ({c['readiness']})")

        # Missing embeddings
        emb_cov = latest.get("embedding_coverage", {})
        missing = {rc: ec for rc, ec in emb_cov.items() if ec.get("missing", 0) > 0}
        if missing:
            print("\n  Missing embeddings:")
            for rc, ec in missing.items():
                print(f"    {rc}: {ec['missing']} missing of {ec['total_images']}")

        # Unknown regions
        unknown = [c for c in coverage if not c.get("metadata", {}).get("known", True)]
        if unknown:
            print("\n  Unknown region codes:")
            for c in unknown:
                print(f"    {c['region_code']}")

        print()


if __name__ == "__main__":
    main()
