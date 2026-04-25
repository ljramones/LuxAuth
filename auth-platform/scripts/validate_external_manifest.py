#!/usr/bin/env python3
"""Validate an external public dataset manifest template (no data required).

Checks manifest structure and field values without requiring the actual dataset
to be downloaded. Use ingest_external_dataset.py --dry-run to validate with data.

Usage:
  python scripts/validate_external_manifest.py --manifest ../datasets/manifests/leadata-manifest.template.yaml
"""

import argparse
import sys
from pathlib import Path

import yaml

REQUIRED_FIELDS = [
    "dataset_name",
    "dataset_version",
    "source_type",
    "source_url",
    "source_license",
    "source_citation",
    "commercial_use_allowed",
    "local_path",
]

SUPPORTED_DATASETS = {"LeaData", "FabricNET"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate external dataset manifest template")
    parser.add_argument("--manifest", required=True, help="Path to manifest YAML")
    parser.add_argument("--allow-commercial-flag", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"FAIL: Manifest not found: {manifest_path}")
        sys.exit(1)

    try:
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"FAIL: YAML parse error: {exc}")
        sys.exit(1)

    if not isinstance(manifest, dict):
        print("FAIL: Manifest root must be a YAML mapping")
        sys.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    # source_type
    source_type = manifest.get("source_type")
    if source_type is not None and source_type != "public_external":
        errors.append(f"source_type must be 'public_external', got '{source_type}'")

    # dataset_version prefix
    dataset_version = manifest.get("dataset_version", "")
    if dataset_version and not dataset_version.startswith("external_"):
        warnings.append(f"dataset_version '{dataset_version}' does not start with 'external_'")

    # commercial_use_allowed
    commercial = manifest.get("commercial_use_allowed")
    if commercial is True and not args.allow_commercial_flag:
        errors.append("commercial_use_allowed is true — requires --allow-commercial-flag or license review")

    # dataset_name
    dataset_name = manifest.get("dataset_name", "")
    if dataset_name and dataset_name not in SUPPORTED_DATASETS:
        warnings.append(f"dataset_name '{dataset_name}' not in supported list: {sorted(SUPPORTED_DATASETS)}")

    # local_path present (syntactic check only)
    local_path = manifest.get("local_path", "")
    if not local_path:
        errors.append("local_path is empty")

    # Empty URL/license/citation warnings
    if manifest.get("source_url") == "":
        warnings.append("source_url is empty — fill in before ingestion")
    if manifest.get("source_license") == "":
        warnings.append("source_license is empty — fill in before ingestion")
    if manifest.get("source_citation") == "":
        warnings.append("source_citation is empty — fill in before ingestion")

    # Print report
    print(f"Manifest: {manifest_path}")
    print(f"Dataset:  {dataset_name} ({dataset_version})")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        print("\nFAIL")
        sys.exit(1)

    print("\nPASS")


if __name__ == "__main__":
    main()
