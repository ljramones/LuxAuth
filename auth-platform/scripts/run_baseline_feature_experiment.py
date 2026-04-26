#!/usr/bin/env python3
"""Run baseline texture feature comparison experiment.

Usage:
  python scripts/run_baseline_feature_experiment.py --dataset external_fabricnet_v0.1.0
  python scripts/run_baseline_feature_experiment.py --dataset external_leadata_v0.1.0 --limit 50
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

# Import normalize from imaging
import importlib.util

from experiments.dataset_loader import load_dataset_records, load_image_bytes
from experiments.experiment_record import create_record, save_record
from experiments.feature_extractors import EXTRACTORS
from experiments.metrics import compute_metrics
from experiments.reporting import print_comparison, write_markdown_report

_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)
normalize_image = _imaging.normalize_image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", default="all")
    parser.add_argument("--extractors", default="texture_baseline_v0.1.0,texture_baseline_v0.2.0")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "baseline-feature-comparison"

    extractor_names = [e.strip() for e in args.extractors.split(",")]

    print(f"Dataset: {args.dataset}")
    print(f"Split: {args.split}")
    print(f"Extractors: {extractor_names}")
    print(f"Output: {output_dir}")

    # Load records
    print("\nLoading dataset records...")
    records = load_dataset_records(args.dataset, split=args.split, limit=args.limit)
    print(f"  Records: {len(records)}")
    if not records:
        print("No records found.")
        sys.exit(1)

    # Download and normalize images
    print("Downloading and normalizing images...")
    images = []
    valid_records = []
    for i, rec in enumerate(records):
        try:
            raw = load_image_bytes(rec["object_uri"])
            norm = normalize_image(raw)
            images.append(norm)
            valid_records.append(rec)
        except Exception as exc:
            print(f"  SKIP {rec['reference_image_id']}: {exc}")
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(records)} loaded")
    print(f"  Valid images: {len(images)}")

    labels = [r["authenticity_status"] for r in valid_records]
    regions = [r["region_code"] for r in valid_records]

    # Run each extractor
    experiment_records = []
    for ext_name in extractor_names:
        if ext_name not in EXTRACTORS:
            print(f"Unknown extractor: {ext_name}")
            continue

        ext_fn = EXTRACTORS[ext_name]
        print(f"\nRunning {ext_name}...")
        embeddings = []
        for img_bytes in images:
            emb = ext_fn(img_bytes)
            embeddings.append(emb)

        dim = len(embeddings[0]) if embeddings else 0
        print(f"  Dimension: {dim}")
        print(f"  Embeddings: {len(embeddings)}")

        metrics = compute_metrics(embeddings, labels, regions)
        print(f"  Cluster separation: {metrics['cluster_separation']}")
        print(f"  NN agreement: {metrics['nn_agreement_rate']:.1%}")

        rec = create_record(
            dataset_version=args.dataset,
            feature_extractor=ext_name,
            embedding_dimension=dim,
            metrics=metrics,
            notes=args.notes,
            split_scope=args.split,
        )
        save_record(rec, output_dir)
        experiment_records.append(rec)

    # Print comparison
    print_comparison(experiment_records)

    # Write report
    report_path = output_dir / f"{args.dataset.replace('.', '_')}__comparison.md"
    write_markdown_report(experiment_records, report_path)
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
