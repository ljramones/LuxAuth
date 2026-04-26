"""Multi-Class Fabric Defect adapter — production-line fabric images.

Expected structure:
  Multi-Class-Fabric-Detection-Dataset/{class_name}/{filename}.png
"""

import os
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
REGION_CODE = "EXTERNAL_FABRIC_TEXTURE"


def load_records(local_path: str | Path) -> list[dict]:
    root = Path(local_path)
    if not root.exists():
        raise FileNotFoundError(f"Multi-Class Fabric path not found: {root}")

    records = []
    for dirpath, _dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        parts = rel.parts

        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            defect_class = parts[0] if len(parts) >= 1 else "unknown"
            sample_id = fpath.stem

            records.append({
                "external_item_id": defect_class,
                "external_image_id": f"mcfd_{defect_class}_{sample_id}",
                "source_file_path": str(fpath.resolve()),
                "primary_label": defect_class,
                "secondary_labels": {},
                "region_code": REGION_CODE,
                "authenticity_status": "PUBLIC_DATASET_CLASS",
                "label_confidence": "medium",
                "provenance_type": "public_dataset",
            })

    if not records:
        raise ValueError(f"No images found in {root}")
    return records
