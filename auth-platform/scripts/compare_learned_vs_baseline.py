#!/usr/bin/env python3
"""Compare learned metric experiment results against texture baseline.

Reads experiment records and baseline feature experiment records, then prints
a comparison table.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/compare_learned_vs_baseline.py --dataset external_leadata_v0.1.0
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Compare learned vs baseline")
    parser.add_argument("--dataset", default=None, help="Filter by dataset version")
    parser.add_argument("--learned-dir", default=None)
    parser.add_argument("--baseline-dir", default=None)
    args = parser.parse_args()

    base = Path(__file__).parent.parent.parent / "experiments" / "outputs"
    learned_dir = Path(args.learned_dir) if args.learned_dir else base / "learned-metric"
    baseline_dir = Path(args.baseline_dir) if args.baseline_dir else base / "baseline-feature-comparison"

    # Load learned metric records
    learned_records = []
    if learned_dir.exists():
        for f in sorted(learned_dir.glob("*__experiment_record.json")):
            rec = json.loads(f.read_text())
            if args.dataset and rec.get("dataset_version") != args.dataset:
                continue
            learned_records.append(rec)

    # Load baseline records
    baseline_records = []
    if baseline_dir.exists():
        for f in sorted(baseline_dir.glob("*__record.json")):
            rec = json.loads(f.read_text())
            if args.dataset and rec.get("dataset_version") != args.dataset:
                continue
            baseline_records.append(rec)

    if not learned_records and not baseline_records:
        print("No experiment records found.")
        sys.exit(0)

    # Group by dataset
    datasets = sorted(set(
        [r["dataset_version"] for r in learned_records] +
        [r["dataset_version"] for r in baseline_records]
    ))

    for ds in datasets:
        print(f"\n{'=' * 100}")
        print(f"  Dataset: {ds}")
        print(f"{'=' * 100}")

        print(f"\n  {'Method':<35} {'Dim':>5} {'ClustSep':>10} {'NN Agree':>10} "
              f"{'R@1':>8} {'R@3':>8} {'R@5':>8}")
        print(f"  {'-' * 95}")

        # Baselines
        for rec in baseline_records:
            if rec["dataset_version"] != ds:
                continue
            m = rec.get("metrics", {})
            name = rec.get("feature_extractor", "baseline")
            print(f"  {name:<35} {m.get('dimension', ''):>5} "
                  f"{m.get('cluster_separation', 0):>10.4f} "
                  f"{m.get('nn_agreement_rate', 0):>9.1%} "
                  f"{m.get('recall_at_1', 0):>8.4f} "
                  f"{m.get('recall_at_3', 0):>8.4f} "
                  f"{m.get('recall_at_5', 0):>8.4f}")

        # Learned
        for rec in learned_records:
            if rec["dataset_version"] != ds:
                continue
            m = rec.get("evaluation_metrics", {})
            if not m:
                print(f"  {rec.get('model_version', 'learned'):<35}  (no evaluation metrics)")
                continue
            name = f"{rec.get('model_version', 'learned')} ({rec.get('backbone', '')})"
            print(f"  {name:<35} {m.get('dimension', ''):>5} "
                  f"{m.get('cluster_separation', 0):>10.4f} "
                  f"{m.get('nn_agreement_rate', 0):>9.1%} "
                  f"{m.get('recall_at_1', 0):>8.4f} "
                  f"{m.get('recall_at_3', 0):>8.4f} "
                  f"{m.get('recall_at_5', 0):>8.4f}")

        print("\n  (diagnostic only — not authentication accuracy)")
        print()


if __name__ == "__main__":
    main()
