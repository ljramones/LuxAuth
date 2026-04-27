#!/usr/bin/env python3
"""Run region-specific analysis on a governed dataset.

Computes per-region coverage, readiness, and embedding diagnostics.
Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/run_region_analysis.py --dataset external_fabricnet_v0.1.0 --model texture_baseline_v0.2.0 --include-external-regions
  python scripts/run_region_analysis.py --dataset smoke_lab_lv_monogram_v0.1.0 --model texture_baseline_v0.1.0
"""

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from experiments.dataset_loader import load_dataset_records
from experiments.region_analysis import (
    compute_embedding_coverage,
    compute_per_region_metrics,
    compute_region_coverage,
    format_coverage_table,
    format_metrics_table,
    is_external_region,
    load_embeddings_for_dataset,
    print_summary_table,
)


def main():
    parser = argparse.ArgumentParser(description="Run region-specific analysis")
    parser.add_argument("--dataset", required=True, help="Dataset version")
    parser.add_argument("--model", default="texture_baseline_v0.2.0", help="Embedding model version")
    parser.add_argument("--split", default="all", help="Dataset split")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--min-region-images", type=int, default=10, help="Minimum images for region metrics")
    parser.add_argument("--include-external-regions", action="store_true", help="Include EXTERNAL_* regions in metrics")
    parser.add_argument("--notes", default="", help="Free-form notes")
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir) if args.output_dir
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "region-analysis"
    )

    print(f"Dataset:  {args.dataset}")
    print(f"Model:    {args.model}")
    print(f"Split:    {args.split}")
    print(f"Min imgs: {args.min_region_images}")
    print(f"External: {'included' if args.include_external_regions else 'excluded from metrics'}")
    print(f"Output:   {output_dir}")

    # Load records
    print("\nLoading dataset records...")
    records = load_dataset_records(args.dataset, split=args.split)
    print(f"  Records: {len(records)}")
    if not records:
        print("No records found.")
        sys.exit(1)

    # Region coverage
    print("\nComputing region coverage...")
    coverage = compute_region_coverage(records)
    for c in coverage:
        print(f"  {c['region_code']}: {c['image_count']} images, "
              f"{c['item_count']} items, readiness={c['readiness']}")

    # Embedding coverage
    print(f"\nChecking embedding coverage for {args.model}...")
    embedding_cov = compute_embedding_coverage(args.dataset, args.model)
    for rc, ec in embedding_cov.items():
        print(f"  {rc}: {ec['embedded']}/{ec['total_images']} "
              f"({ec['coverage_pct']}%)"
              f"{' MISSING ' + str(ec['missing']) if ec['missing'] > 0 else ''}")

    # Load embeddings and compute per-region metrics
    print("\nLoading embeddings...")
    embeddings = load_embeddings_for_dataset(args.dataset, args.model)
    print(f"  Loaded: {len(embeddings)} embeddings")

    # Filter records for metrics
    metric_records = records
    if not args.include_external_regions:
        metric_records = [r for r in records if not is_external_region(r["region_code"])]
        excluded = len(records) - len(metric_records)
        if excluded:
            print(f"  Excluded {excluded} external-region records from metrics")

    print("\nComputing per-region metrics...")
    region_metrics = compute_per_region_metrics(
        metric_records if metric_records else records,
        embeddings,
        min_images=args.min_region_images,
    )
    # If we excluded external but had no non-external, fall back to all
    if not region_metrics and metric_records != records:
        print("  No non-external regions found; including external regions")
        region_metrics = compute_per_region_metrics(
            records, embeddings, min_images=args.min_region_images,
        )

    for rm in region_metrics:
        m = rm.get("metrics")
        if m:
            print(f"  {rm['region_code']}: cluster_sep={m['cluster_separation']:.4f}, "
                  f"nn_agree={m['nn_agreement_rate']:.1%}")
        else:
            print(f"  {rm['region_code']}: {rm.get('note', 'no metrics')}")

    # Console summary
    print_summary_table(coverage, embedding_cov, region_metrics)

    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    ds_tag = args.dataset.replace(".", "_")

    # JSON
    analysis = {
        "dataset_version": args.dataset,
        "model_version": args.model,
        "split": args.split,
        "timestamp": now.isoformat(),
        "include_external_regions": args.include_external_regions,
        "min_region_images": args.min_region_images,
        "total_records": len(records),
        "total_embeddings": len(embeddings),
        "coverage": coverage,
        "embedding_coverage": embedding_cov,
        "region_metrics": [
            {
                "region_code": rm["region_code"],
                "embedding_count": rm["embedding_count"],
                "note": rm.get("note", ""),
                "metrics": rm.get("metrics"),
            }
            for rm in region_metrics
        ],
        "notes": args.notes,
    }
    json_path = output_dir / f"{ds_tag}__region_analysis.json"
    json_path.write_text(json.dumps(analysis, indent=2, default=str))

    # Markdown report
    report_lines = [
        "# Region-Specific Analysis Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> Results are diagnostic only. They do not prove authentication accuracy.",
        "",
        "## Configuration",
        "",
        f"- **Dataset:** `{args.dataset}`",
        f"- **Model:** `{args.model}`",
        f"- **Split:** {args.split}",
        f"- **Total records:** {len(records)}",
        f"- **Total embeddings:** {len(embeddings)}",
        f"- **External regions:** {'included' if args.include_external_regions else 'excluded from metrics'}",
        "",
        "## Region Coverage",
        "",
        format_coverage_table(coverage),
        "",
        "## Per-Region Metrics",
        "",
        format_metrics_table(region_metrics),
        "",
        "## Limitations",
        "",
        "- Readiness is based on image count only; label quality, item diversity,",
        "  split quality, and provenance also matter.",
        "- Single-label regions (e.g., public external datasets) have limited",
        "  same/different-label metrics.",
        "- These results are diagnostic only and do not prove authentication accuracy.",
        "",
    ]
    md_path = output_dir / f"{ds_tag}__region_analysis.md"
    md_path.write_text("\n".join(report_lines) + "\n")

    # CSV
    csv_path = output_dir / f"{ds_tag}__region_metrics.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "region_code", "image_count", "item_count", "readiness",
            "embedded", "coverage_pct",
            "dimension", "cluster_separation", "nn_agreement_rate",
            "recall_at_1", "recall_at_3", "recall_at_5",
            "same_label_mean", "diff_label_mean", "norm_mean", "note",
        ])
        cov_map = {c["region_code"]: c for c in coverage}
        met_map = {rm["region_code"]: rm for rm in region_metrics}
        for rc in sorted(set(list(cov_map.keys()) + list(met_map.keys()))):
            c = cov_map.get(rc, {})
            rm = met_map.get(rc, {})
            m = rm.get("metrics") or {}
            ec = embedding_cov.get(rc, {})
            writer.writerow([
                rc,
                c.get("image_count", 0),
                c.get("item_count", 0),
                c.get("readiness", ""),
                ec.get("embedded", 0),
                ec.get("coverage_pct", 0),
                m.get("dimension", ""),
                m.get("cluster_separation", ""),
                m.get("nn_agreement_rate", ""),
                m.get("recall_at_1", ""),
                m.get("recall_at_3", ""),
                m.get("recall_at_5", ""),
                m.get("same_label_mean", ""),
                m.get("diff_label_mean", ""),
                m.get("norm_mean", ""),
                rm.get("note", ""),
            ])

    print(f"\nJSON:   {json_path}")
    print(f"Report: {md_path}")
    print(f"CSV:    {csv_path}")


if __name__ == "__main__":
    main()
