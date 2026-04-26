#!/usr/bin/env python3
"""Run preprocessing comparison experiment on a governed dataset.

Compares preprocessing strategies using the same feature extractor to understand
whether center-crop normalization is sufficient or whether alternative strategies
improve embedding behavior.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/run_preprocessing_experiment.py --dataset external_fabricnet_v0.1.0
  python scripts/run_preprocessing_experiment.py --dataset external_leadata_v0.1.0 --extractor texture_baseline_v0.2.0
  python scripts/run_preprocessing_experiment.py --dataset external_fabricnet_v0.1.0 --strategies center_crop_512,padded_resize_512 --limit 50
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from experiments.dataset_loader import load_dataset_records, load_image_bytes
from experiments.experiment_record import create_record, save_record
from experiments.preprocessing import ALL_STRATEGY_NAMES, set_max_tiles
from experiments.preprocessing_experiment import (
    format_comparison_table,
    print_comparison_table,
    run_all_strategies,
)


def main():
    parser = argparse.ArgumentParser(description="Run preprocessing comparison experiment")
    parser.add_argument("--dataset", required=True, help="Dataset version (e.g., external_fabricnet_v0.1.0)")
    parser.add_argument("--extractor", default="texture_baseline_v0.2.0", help="Feature extractor version")
    parser.add_argument("--strategies", default=None, help="Comma-separated strategy names (default: all)")
    parser.add_argument("--split", default="all", help="Dataset split (default: all)")
    parser.add_argument("--limit", type=int, default=None, help="Max images to process")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--progress-every", type=int, default=50, help="Print progress every N images (default: 50)")
    parser.add_argument("--max-tiles", type=int, default=0, help="Max tiles for tile_224_average (0=no limit)")
    parser.add_argument("--notes", default="", help="Free-form notes")
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir) if args.output_dir
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "preprocessing-comparison"
    )

    strategy_names = [s.strip() for s in args.strategies.split(",")] if args.strategies else ALL_STRATEGY_NAMES

    # Validate strategy names
    for name in strategy_names:
        if name not in ALL_STRATEGY_NAMES:
            print(f"ERROR: Unknown strategy '{name}'. Available: {ALL_STRATEGY_NAMES}")
            sys.exit(1)

    # Configure max tiles before any strategy runs
    if args.max_tiles > 0:
        set_max_tiles(args.max_tiles)

    print(f"Dataset:    {args.dataset}")
    print(f"Extractor:  {args.extractor}")
    print(f"Strategies: {strategy_names}")
    print(f"Split:      {args.split}")
    if args.limit:
        print(f"Limit:      {args.limit} images")
    if args.max_tiles > 0:
        print(f"Max tiles:  {args.max_tiles}")
    print(f"Output:     {output_dir}")

    # Load records
    print("\nLoading dataset records...")
    records = load_dataset_records(args.dataset, split=args.split, limit=args.limit)
    print(f"  Records: {len(records)}")
    if not records:
        print("No records found.")
        sys.exit(1)

    # Download raw images — prefer original object_uri
    print("Downloading images...")
    images = []
    valid_records = []
    for i, rec in enumerate(records):
        try:
            raw = load_image_bytes(rec["object_uri"])
            images.append(raw)
            valid_records.append(rec)
        except Exception as exc:
            print(f"  SKIP {rec['reference_image_id']}: {exc}")
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(records)} loaded")
    print(f"  Valid images: {len(images)}")

    if not images:
        print("No valid images loaded.")
        sys.exit(1)

    labels = [r["authenticity_status"] for r in valid_records]
    regions = [r["region_code"] for r in valid_records]

    # Run strategies
    print("\nRunning preprocessing strategies...")
    results = run_all_strategies(images, labels, regions, args.extractor, strategy_names, args.progress_every)

    # Print comparison
    print_comparison_table(results)

    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    ds_tag = args.dataset.replace(".", "_")

    # Save individual experiment records
    experiment_records = []
    for r in results:
        rec = create_record(
            dataset_version=args.dataset,
            feature_extractor=args.extractor,
            embedding_dimension=r["embedding_dimension"],
            metrics=r["metrics"],
            notes=args.notes,
            split_scope=args.split,
            preprocessing_version=r["strategy"],
        )
        rec["strategy"] = r["strategy"]
        rec["runtime_seconds"] = r["runtime_seconds"]
        save_record(rec, output_dir)
        experiment_records.append(rec)

    # Save combined metrics
    metrics_path = output_dir / f"{ds_tag}__{args.extractor.replace('.', '_')}__preprocessing_metrics.json"
    metrics_data = {
        "dataset_version": args.dataset,
        "extractor": args.extractor,
        "timestamp": now.isoformat(),
        "strategies": [],
    }
    for r in results:
        metrics_data["strategies"].append({
            "strategy": r["strategy"],
            "embedding_dimension": r["embedding_dimension"],
            "runtime_seconds": r["runtime_seconds"],
            "metrics": r["metrics"],
        })
    metrics_path.write_text(json.dumps(metrics_data, indent=2, default=str))

    # Write markdown report
    report_path = output_dir / f"{ds_tag}__preprocessing_report.md"
    report_lines = [
        "# Preprocessing Comparison Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> Results are diagnostic only. They do not prove authentication accuracy.",
        "> Public datasets are not luxury authentication datasets.",
        "",
        "## Configuration",
        "",
        f"- **Dataset:** `{args.dataset}`",
        f"- **Extractor:** `{args.extractor}`",
        f"- **Split:** {args.split}",
        f"- **Images:** {len(images)}",
        f"- **Strategies:** {len(results)}",
        "",
        "## Results",
        "",
        format_comparison_table(results),
        "",
        "## Top Strategies",
        "",
    ]

    # Identify top strategies
    by_cluster = sorted(results, key=lambda r: r["metrics"].get("cluster_separation", 0), reverse=True)
    by_nn = sorted(results, key=lambda r: r["metrics"].get("nn_agreement_rate", 0), reverse=True)
    by_recall = sorted(results, key=lambda r: r["metrics"].get("recall_at_1", 0), reverse=True)

    report_lines.append(f"- **Best cluster separation:** {by_cluster[0]['strategy']} "
                        f"({by_cluster[0]['metrics'].get('cluster_separation', 0):.4f})")
    report_lines.append(f"- **Best NN agreement:** {by_nn[0]['strategy']} "
                        f"({by_nn[0]['metrics'].get('nn_agreement_rate', 0):.1%})")
    report_lines.append(f"- **Best recall@1:** {by_recall[0]['strategy']} "
                        f"({by_recall[0]['metrics'].get('recall_at_1', 0):.4f})")

    report_lines.extend([
        "",
        "## Limitations",
        "",
        "- Public datasets such as FabricNET and LeaData are not authentic-vs-counterfeit luxury datasets.",
        "- These results validate preprocessing behavior on texture data, not authentication accuracy.",
        "- Center-crop remains the backend default until evidence from real microscopy data supports a change.",
        "",
    ])
    report_path.write_text("\n".join(report_lines) + "\n")

    print(f"Metrics: {metrics_path}")
    print(f"Report:  {report_path}")
    print(f"Records: {output_dir}")


if __name__ == "__main__":
    main()
