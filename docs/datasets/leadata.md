# LeaData — Microscopic Leather Texture Dataset

## Intended Use in LuxAuth

LeaData provides microscopic images of leather surfaces from different animal species.
It is useful for testing whether the LuxAuth pipeline can:

- Ingest and normalize real microscopic images
- Generate texture embeddings that cluster by leather type
- Perform nearest-neighbor search that returns same-species images
- Train metric-learning models that separate leather classes

**This is NOT an authentic-vs-counterfeit dataset.** It validates pipeline behavior
on real microscopic textures, not luxury goods authentication.

## Expected Local Structure

```text
datasets/external/leadata/
├── images/
│   ├── cow/
│   │   ├── belly/
│   │   │   ├── sample_001.png
│   │   │   └── ...
│   │   └── back/
│   └── goat/
│       └── ...
└── index.csv  (optional — if folder structure alone is insufficient)
```

## Manifest

Use `datasets/manifests/leadata-manifest.template.yaml`.

**Dataset version prefix:** `external_leadata_v0.1.0`

## Region Code

`EXTERNAL_LEATHER_TEXTURE` — distinct from luxury authentication regions.

## Labels

- `primary_label`: species (cow, goat, sheep, etc.)
- `secondary_labels`: body_part, sample_id

## Ingestion

```bash
cd auth-platform
make ingest-external-dataset MANIFEST=../datasets/manifests/leadata-manifest.yaml
```
