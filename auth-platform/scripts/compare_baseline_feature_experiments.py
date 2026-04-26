#!/usr/bin/env python3
"""Compare baseline feature experiment records.

Usage:
  python scripts/compare_baseline_feature_experiments.py --dataset external_fabricnet_v0.1.0
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from experiments.reporting import print_comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "baseline-feature-comparison"

    if not output_dir.exists():
        print(f"No experiments found at {output_dir}")
        sys.exit(0)

    records = []
    for f in sorted(output_dir.glob("*__record.json")):
        rec = json.loads(f.read_text())
        if args.dataset and rec.get("dataset_version") != args.dataset:
            continue
        records.append(rec)

    if not records:
        print("No matching experiment records found.")
        sys.exit(0)

    # Group by dataset
    datasets = sorted(set(r["dataset_version"] for r in records))
    for ds in datasets:
        ds_records = [r for r in records if r["dataset_version"] == ds]
        print(f"\n{'=' * 70}")
        print(f"  Dataset: {ds}")
        print(f"{'=' * 70}")
        print_comparison(ds_records)


if __name__ == "__main__":
    main()
