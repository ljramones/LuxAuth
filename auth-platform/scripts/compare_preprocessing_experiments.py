#!/usr/bin/env python3
"""Compare preprocessing experiment results.

Reads generated metrics JSON files and prints a comparison table sorted by
cluster separation or NN agreement.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/compare_preprocessing_experiments.py
  python scripts/compare_preprocessing_experiments.py --dataset external_fabricnet_v0.1.0
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from experiments.preprocessing_experiment import print_comparison_table


def main():
    parser = argparse.ArgumentParser(description="Compare preprocessing experiments")
    parser.add_argument("--dataset", default=None, help="Filter by dataset version")
    parser.add_argument("--latest-for-dataset", default=None, help="Show only latest run for this dataset")
    parser.add_argument("--reports", default=None, help="Path to reports directory")
    args = parser.parse_args()

    reports_dir = (
        Path(args.reports) if args.reports
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "preprocessing-comparison"
    )

    if not reports_dir.exists():
        print(f"No experiments found at {reports_dir}")
        sys.exit(0)

    # Load all preprocessing metrics files
    all_runs = []
    for f in sorted(reports_dir.glob("*__preprocessing_metrics.json")):
        data = json.loads(f.read_text())
        if args.dataset and data.get("dataset_version") != args.dataset:
            continue
        if args.latest_for_dataset and data.get("dataset_version") != args.latest_for_dataset:
            continue
        all_runs.append(data)

    if not all_runs:
        print("No matching preprocessing experiment results found.")
        sys.exit(0)

    # Group by dataset
    datasets = sorted(set(r["dataset_version"] for r in all_runs))

    for ds in datasets:
        ds_runs = [r for r in all_runs if r["dataset_version"] == ds]
        # Use the latest run per dataset
        latest = max(ds_runs, key=lambda r: r.get("timestamp", ""))

        print(f"\n{'=' * 100}")
        print(f"  Dataset: {ds}")
        print(f"  Extractor: {latest['extractor']}")
        print(f"  Timestamp: {latest.get('timestamp', 'N/A')}")
        print(f"{'=' * 100}")

        results = []
        for s in latest["strategies"]:
            results.append({
                "strategy": s["strategy"],
                "extractor": latest["extractor"],
                "embedding_dimension": s["embedding_dimension"],
                "runtime_seconds": s.get("runtime_seconds", 0),
                "metrics": s["metrics"],
            })

        print_comparison_table(results)

        # Identify top strategies
        by_cluster = sorted(results, key=lambda r: r["metrics"].get("cluster_separation", 0), reverse=True)
        by_nn = sorted(results, key=lambda r: r["metrics"].get("nn_agreement_rate", 0), reverse=True)
        by_recall = sorted(results, key=lambda r: r["metrics"].get("recall_at_1", 0), reverse=True)

        print("  Top strategies (diagnostic only — not authentication accuracy):")
        print(f"    Cluster separation: {by_cluster[0]['strategy']} ({by_cluster[0]['metrics'].get('cluster_separation', 0):.4f})")
        print(f"    NN agreement:       {by_nn[0]['strategy']} ({by_nn[0]['metrics'].get('nn_agreement_rate', 0):.1%})")
        print(f"    Recall@1:           {by_recall[0]['strategy']} ({by_recall[0]['metrics'].get('recall_at_1', 0):.4f})")
        print()


if __name__ == "__main__":
    main()
