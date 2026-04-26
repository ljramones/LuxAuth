"""Produce standard experiment record."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


def create_record(
    dataset_version: str,
    feature_extractor: str,
    embedding_dimension: int,
    metrics: dict,
    notes: str = "",
    split_scope: str = "all",
    preprocessing_version: str = "normalize_image_v0.1.0",
) -> dict:
    return {
        "experiment_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset_version": dataset_version,
        "feature_extractor": feature_extractor,
        "embedding_dimension": embedding_dimension,
        "preprocessing_version": preprocessing_version,
        "split_scope": split_scope,
        "metrics": metrics,
        "notes": notes,
    }


def save_record(record: dict, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ext_name = record["feature_extractor"].replace(".", "_")
    ds_name = record["dataset_version"].replace(".", "_")
    prefix = f"{ds_name}__{ext_name}"

    record_path = out / f"{prefix}__record.json"
    record_path.write_text(json.dumps(record, indent=2))
    return record_path
