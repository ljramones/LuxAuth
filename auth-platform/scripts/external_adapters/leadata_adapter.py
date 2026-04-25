"""LeaData adapter — microscopic leather texture images.

LeaData V1 layout:
  LeaData-V1/{Species}/{SamplePrefix} ({index}).jpg

Examples:
  LeaData-V1/Cow/CBTS3 (1).jpg
  LeaData-V1/Goat/GBTS16 (105).jpg
  LeaData-V1/Sheep/SBTS6 (57).jpg
  LeaData-V1/Buffalo/BBTS1 (12).jpg

Species is inferred from the top-level folder name.
Sample group is inferred from the filename prefix before the space/parenthesis.
"""

import re
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
REGION_CODE = "EXTERNAL_LEATHER_TEXTURE"

# Extract sample prefix: "CBTS3" from "CBTS3 (1).jpg" or "CBTS3.jpg"
SAMPLE_PREFIX_PATTERN = re.compile(r"^([A-Za-z]+\d+)")


def load_records(local_path: str | Path) -> list[dict]:
    """Walk the LeaData directory and return normalized ingestion records."""
    root = Path(local_path)
    if not root.exists():
        raise FileNotFoundError(f"LeaData path not found: {root}")

    records = []

    for species_dir in sorted(root.iterdir()):
        if not species_dir.is_dir():
            continue

        species = species_dir.name  # Cow, Goat, Sheep, Buffalo

        for fpath in sorted(species_dir.iterdir()):
            if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            fname = fpath.stem  # e.g. "CBTS3 (1)"
            m = SAMPLE_PREFIX_PATTERN.match(fname)
            sample_group = m.group(1) if m else fname.split()[0] if " " in fname else fname

            # external_item_id groups images by species + sample group
            external_item_id = f"{species}_{sample_group}"

            records.append({
                "external_item_id": external_item_id,
                "external_image_id": f"{species}_{fname}".replace(" ", "_"),
                "source_file_path": str(fpath.resolve()),
                "primary_label": species,
                "secondary_labels": {"sample_group": sample_group},
                "region_code": REGION_CODE,
                "authenticity_status": "PUBLIC_DATASET_CLASS",
                "label_confidence": "medium",
                "provenance_type": "public_dataset",
            })

    if not records:
        raise ValueError(
            f"No images found in {root}. Expected: {{Species}}/{{SamplePrefix}} ({{index}}).jpg"
        )

    return records
