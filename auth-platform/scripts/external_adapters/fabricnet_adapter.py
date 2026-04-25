"""FabricNET adapter — microscopic woven fabric texture images.

Walks the local FabricNET directory and produces normalized ingestion records.
Expected structure:
  fabricnet/images/{fabric_type}/{filename}.{ext}
  or
  fabricnet/{fabric_type}/{filename}.{ext}

Falls back to flat directory listing if structure is ambiguous.
"""

import os
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
REGION_CODE = "EXTERNAL_FABRIC_TEXTURE"


def load_records(local_path: str | Path) -> list[dict]:
    """Walk the FabricNET directory and return normalized ingestion records."""
    root = Path(local_path)
    if not root.exists():
        raise FileNotFoundError(f"FabricNET path not found: {root}")

    records = []

    images_dir = root / "images"
    if not images_dir.exists():
        images_dir = root

    for dirpath, _dirnames, filenames in os.walk(images_dir):
        rel = Path(dirpath).relative_to(images_dir)
        parts = rel.parts

        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            fabric_type = parts[0] if len(parts) >= 1 else "unknown"
            sample_id = fpath.stem

            external_item_id = fabric_type

            records.append({
                "external_item_id": external_item_id,
                "external_image_id": f"{fabric_type}_{sample_id}",
                "source_file_path": str(fpath.resolve()),
                "primary_label": fabric_type,
                "secondary_labels": {},
                "region_code": REGION_CODE,
                "authenticity_status": "PUBLIC_DATASET_CLASS",
                "label_confidence": "medium",
                "provenance_type": "public_dataset",
            })

    if not records:
        raise ValueError(
            f"No images found in {root}. Expected structure: images/{{fabric_type}}/{{file}} "
            "or a flat directory of image files."
        )

    return records
