# Dataset Adapters

Dataset adapters translate external public dataset folder structures into the
normalized record format expected by the LuxAuth backend ingestion pipeline.

Executable adapter code lives in `auth-platform/scripts/external_adapters/`.
This directory contains documentation only.

## Available Adapters

| Adapter | Dataset | Region Code | Notes |
|---|---|---|---|
| leadata_adapter | LeaData | EXTERNAL_LEATHER_TEXTURE | Microscopic leather textures |
| fabricnet_adapter | FabricNET | EXTERNAL_FABRIC_TEXTURE | Microscopic woven fabric textures |
| tilda_adapter | TILDA | EXTERNAL_FABRIC_TEXTURE | Industrial textile textures with defects |
| tfd_adapter | TFD | EXTERNAL_FABRIC_TEXTURE | Scanned fabric patches |
| multiclass_fabric_adapter | MultiClassFabric | EXTERNAL_FABRIC_TEXTURE | Production-line fabric defects |
| aitex_adapter | AITEX | EXTERNAL_FABRIC_TEXTURE | Industrial fabric defect database |
| leather_defect_adapter | LeatherDefect | EXTERNAL_LEATHER_TEXTURE | Leather surface defects |
| chanel_macro_adapter | ChanelMacro | EXTERNAL_LUXURY_MACRO | Macro product photos (deferred) |

## Adapter Output Format

Each adapter produces a list of records:
```python
{
    "external_item_id": "sample_001",
    "external_image_id": "sample_001_img_01",
    "source_file_path": "/absolute/path/to/image.png",
    "primary_label": "cow",
    "secondary_labels": {"body_part": "belly", "sample_id": "001"},
    "region_code": "EXTERNAL_LEATHER_TEXTURE",
    "authenticity_status": "PUBLIC_DATASET_CLASS",
    "label_confidence": "medium",
    "provenance_type": "public_dataset",
}
```
