# FabricNET — Microscopic Woven Fabric Texture Dataset

## Intended Use in LuxAuth

FabricNET provides microscopic images of woven fabric samples with metadata about
weave type, thread counts, and mass. It is useful for testing whether the LuxAuth
pipeline can:

- Process fabric/canvas-like microscopic textures
- Generate embeddings that cluster by fabric type
- Distinguish different weave patterns via nearest-neighbor search
- Train metric-learning models on structured textile features

**This is NOT an authentic-vs-counterfeit dataset.** It validates pipeline behavior
on real microscopic fabric textures.

## Expected Local Structure

```text
datasets/external/fabricnet/
├── images/
│   ├── plain_weave/
│   │   ├── sample_001.png
│   │   └── ...
│   ├── twill_weave/
│   └── satin_weave/
└── metadata.csv  (optional — fabric properties per sample)
```

## Manifest

Use `datasets/manifests/fabricnet-manifest.template.yaml`.

**Dataset version prefix:** `external_fabricnet_v0.1.0`

## Region Code

`EXTERNAL_FABRIC_TEXTURE` — distinct from luxury authentication regions.

## Labels

- `primary_label`: fabric_type (plain_weave, twill_weave, satin_weave, etc.)
- `secondary_labels`: weave, warp_count, weft_count, mass

## Ingestion

```bash
cd auth-platform
make ingest-external-dataset MANIFEST=../datasets/manifests/fabricnet-manifest.yaml
```
