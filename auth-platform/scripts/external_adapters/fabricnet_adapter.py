"""FabricNET adapter — microscopic woven fabric texture images.

Actual FabricNET layout is a flat directory of W001.jpg through W130.jpg
plus FabricNet_parameters.xlsx with metadata per sample.

If the XLSX is available and openpyxl is installed, fabric parameters are
read as secondary labels. Otherwise each image becomes its own item with
sample ID inferred from filename.
"""

import re
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
REGION_CODE = "EXTERNAL_FABRIC_TEXTURE"
SAMPLE_PATTERN = re.compile(r"^(W\d+)", re.IGNORECASE)


def _try_load_xlsx(xlsx_path: Path) -> dict[str, dict]:
    """Try to load FabricNet_parameters.xlsx. Returns {sample_id: {param: value}}."""
    try:
        import openpyxl  # type: ignore[import-untyped]
    except ImportError:
        return {}

    if not xlsx_path.exists():
        return {}

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return {}

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return {}

    headers = [str(h).strip().lower() if h else f"col{i}" for i, h in enumerate(rows[0])]
    result: dict[str, dict] = {}
    for row in rows[1:]:
        row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        # Try to find sample ID column
        sample_id = None
        for key in ("sample", "sample_id", "id", "name", "fabric", headers[0]):
            val = row_dict.get(key)
            if val is not None:
                sample_id = str(val).strip()
                break
        if sample_id:
            result[sample_id] = {k: str(v) if v is not None else "" for k, v in row_dict.items()}

    wb.close()
    return result


def load_records(local_path: str | Path) -> list[dict]:
    """Walk the FabricNET directory and return normalized ingestion records."""
    root = Path(local_path)
    if not root.exists():
        raise FileNotFoundError(f"FabricNET path not found: {root}")

    # Try to load parameters spreadsheet
    xlsx_meta = _try_load_xlsx(root / "FabricNet_parameters.xlsx")
    if xlsx_meta:
        print(f"  FabricNET: loaded metadata for {len(xlsx_meta)} samples from XLSX")

    records = []

    for fpath in sorted(root.iterdir()):
        if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        sample_id = fpath.stem  # e.g. "W001"
        m = SAMPLE_PATTERN.match(sample_id)
        canonical_id = m.group(1) if m else sample_id

        # Each image is its own item (FabricNET has one image per sample)
        secondary = {}
        if canonical_id in xlsx_meta:
            secondary = xlsx_meta[canonical_id]
        elif sample_id in xlsx_meta:
            secondary = xlsx_meta[sample_id]

        records.append({
            "external_item_id": canonical_id,
            "external_image_id": f"fabricnet_{canonical_id}",
            "source_file_path": str(fpath.resolve()),
            "primary_label": canonical_id,
            "secondary_labels": secondary,
            "region_code": REGION_CODE,
            "authenticity_status": "PUBLIC_DATASET_CLASS",
            "label_confidence": "medium",
            "provenance_type": "public_dataset",
        })

    if not records:
        raise ValueError(
            f"No images found in {root}. Expected flat directory with W001.jpg, W002.jpg, etc."
        )

    return records
