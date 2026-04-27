#!/usr/bin/env python3
"""Compare OOD experiment results.

Reads generated OOD summary JSON files and prints a method comparison table.
Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/compare_ood_experiments.py
  python scripts/compare_ood_experiments.py --latest
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Compare OOD experiments")
    parser.add_argument("--reports", default=None, help="Path to reports directory")
    parser.add_argument("--latest", action="store_true", help="Show only the latest run per pair")
    args = parser.parse_args()

    reports_dir = (
        Path(args.reports) if args.reports
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "ood"
    )

    if not reports_dir.exists():
        print(f"No OOD experiments found at {reports_dir}")
        sys.exit(0)

    all_runs = []
    for f in sorted(reports_dir.glob("*__ood_summary.json")):
        data = json.loads(f.read_text())
        all_runs.append(data)

    if not all_runs:
        print("No OOD experiment results found.")
        sys.exit(0)

    # Group by experiment pair
    pairs: dict[str, list[dict]] = {}
    for r in all_runs:
        key = f"{r['in_dataset']} vs {r['out_dataset']}"
        pairs.setdefault(key, []).append(r)

    methods = ["max_similarity", "mean_topk", "similarity_gap", "knn_density", "mahalanobis", "lof"]

    for pair_key, runs in sorted(pairs.items()):
        if args.latest:
            runs = [max(runs, key=lambda r: r.get("timestamp", ""))]

        for run in runs:
            print(f"\n{'=' * 110}")
            print(f"  {pair_key}")
            print(f"  Model: {run['model']}  K: {run['k']}  "
                  f"ID: {run['id_count']}  OOD: {run['ood_count']}  Ref: {run['ref_count']}")
            print(f"{'=' * 110}")

            print(f"\n  {'Method':<18} {'AUROC':>7} {'ID mean':>8} {'OOD mean':>9} "
                  f"{'Sep':>7} {'Overlap':>8} {'Thresh':>8} {'FalseOOD':>9} {'MissOOD':>8}")
            print(f"  {'-' * 100}")

            summaries = run.get("method_summaries", {})
            for m in methods:
                s = summaries.get(m, {})
                if not s:
                    continue
                marker = " *" if m == run.get("best_method") else "  "
                print(f" {marker}{m:<16} {s.get('auroc', 0):>7.4f} "
                      f"{s.get('id_mean', 0):>8.4f} {s.get('ood_mean', 0):>9.4f} "
                      f"{s.get('separation', 0):>7.4f} {s.get('overlap', 0):>8.4f} "
                      f"{s.get('best_threshold', 0):>8.4f} "
                      f"{s.get('best_false_ood_rate', 0):>9.4f} "
                      f"{s.get('best_missed_ood_rate', 0):>8.4f}")

            print(f"\n  Best by AUROC: {run.get('best_method', '?')} "
                  f"({summaries.get(run.get('best_method', ''), {}).get('auroc', 0):.4f})")
            print("  (diagnostic only — not authentication accuracy)")
            print()


if __name__ == "__main__":
    main()
