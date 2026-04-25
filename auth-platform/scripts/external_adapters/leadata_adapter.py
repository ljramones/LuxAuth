"""LeaData adapter — microscopic leather texture images.

Walks the local LeaData directory and produces normalized ingestion records.
Expected structure:
  leadata/images/{species}/{body_part}/{sample_id}.{ext}
  or
  leadata/{species}/{filename}.{ext}

Falls back to flat directory listing if structure is ambiguous.
"""

import os
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
REGION_CODE = "EXTERNAL_LEATHER_TEXTURE"


def load_records(local_path: str | Path) -> list[dict]:
    """Walk the LeaData directory and return normalized ingestion records."""
    root = Path(local_path)
    if not root.exists():
        raise FileNotFoundError(f"LeaData path not found: {root}")

    records = []
    seen_items = set()

    # Try structured path: {root}/images/{species}/{body_part}/{file}
    images_dir = root / "images"
    if not images_dir.exists():
        images_dir = root  # fall back to root

    for dirpath, _dirnames, filenames in os.walk(images_dir):
        rel = Path(dirpath).relative_to(images_dir)
        parts = rel.parts

        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            # Infer labels from path structure
            species = parts[0] if len(parts) >= 1 else "unknown"
            body_part = parts[1] if len(parts) >= 2 else "unknown"
            sample_id = fpath.stem

            external_item_id = f"{species}_{body_part}" if body_part != "unknown" else species
            seen_items.add(external_item_id)

            records.append({
                "external_item_id": external_item_id,
                "external_image_id": f"{external_item_id}_{sample_id}",
                "source_file_path": str(fpath.resolve()),
                "primary_label": species,
                "secondary_labels": {"body_part": body_part, "sample_id": sample_id},
                "region_code": REGION_CODE,
                "authenticity_status": "PUBLIC_DATASET_CLASS",
                "label_confidence": "medium",
                "provenance_type": "public_dataset",
            })

    if not records:
        raise ValueError(
            f"No images found in {root}. Expected structure: images/{{species}}/{{body_part}}/{{file}} "
            "or a flat directory of image files. If the dataset uses a CSV index, "
            "that format is not yet supported."
        )

    return records
