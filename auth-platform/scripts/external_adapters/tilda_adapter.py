"""TILDA adapter — industrial textile texture images with defects.

Expected structure:
  tilda_CD1+CD2/{fabric_type_or_subfolder}/{filename}.tif
  or flat directory of TIF files.
"""

import os
from pathlib import Path

IMAGE_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"}
REGION_CODE = "EXTERNAL_FABRIC_TEXTURE"


def load_records(local_path: str | Path) -> list[dict]:
    root = Path(local_path)
    if not root.exists():
        raise FileNotFoundError(f"TILDA path not found: {root}")

    records = []
    for dirpath, _dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        parts = rel.parts

        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            fabric_type = parts[0] if len(parts) >= 1 else "unknown"
            sample_id = fpath.stem

            # Infer defect status from filename or folder if possible
            name_lower = fname.lower()
            label = "DEFECTIVE_TEXTURE" if ("defect" in name_lower or "fehler" in name_lower) else "NORMAL_TEXTURE"

            records.append({
                "external_item_id": fabric_type,
                "external_image_id": f"tilda_{fabric_type}_{sample_id}",
                "source_file_path": str(fpath.resolve()),
                "primary_label": fabric_type,
                "secondary_labels": {"defect_status": label},
                "region_code": REGION_CODE,
                "authenticity_status": "PUBLIC_DATASET_CLASS",
                "label_confidence": "medium",
                "provenance_type": "public_dataset",
            })

    if not records:
        raise ValueError(f"No images found in {root}. Expected TIF files in subdirectories.")

    return records
