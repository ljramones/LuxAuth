# Public Dataset Evaluation Plan

## Why Public Datasets

Before a microscope arrives, public texture/material datasets let us validate:

1. **Ingestion pipeline** — real images through quality, normalization, embedding
2. **Embedding behavior** — do texture features cluster by class?
3. **Vector search** — does pgvector nearest-neighbor return same-class images?
4. **Metric learning** — can contrastive training separate classes?
5. **Evaluation harness** — do metrics compute correctly on real data?
6. **Diagnostics** — cluster separation, NN agreement, threshold calibration

## What Public Datasets Cannot Validate

- Authentic vs. counterfeit luxury goods discrimination
- Microscopic manufacturing signature detection
- Real-world authentication accuracy
- Production capture protocol behavior

Public datasets test the **pipeline**, not the **authentication capability**.

## Recommended Order

| Priority | Dataset | Purpose |
|---|---|---|
| 1 | LeaData | Microscopic leather textures — closest to luxury leather grain |
| 2 | FabricNET | Microscopic woven fabric — closest to canvas/textile analysis |
| 3 | TILDA/AITEX | Textile defect detection — different task but similar images |
| 4 | DTD | Describable Textures — general texture classification |
| 5 | LFFD | Luxury fashion macro images — requires extra license caution |

## Workflow

```bash
# 1. Download dataset locally (not committed)
# 2. Place under datasets/external/{dataset_name}/
# 3. Fill in manifest template

cd auth-platform

# 4. Dry run to validate
make ingest-external-dataset-dry-run MANIFEST=../datasets/manifests/leadata-manifest.yaml

# 5. Ingest
make ingest-external-dataset MANIFEST=../datasets/manifests/leadata-manifest.yaml

# 6. Embed + evaluate
make reembed-reference-data DATASET=external_leadata_v0.1.0 MODEL=texture_baseline_v0.1.0
make run-evaluation MODEL=texture_baseline_v0.1.0
make analyze-embeddings MODEL=texture_baseline_v0.1.0
```

## Separation from Other Data

| Dataset Type | Prefix | Source | Purpose |
|---|---|---|---|
| Synthetic | `synthetic_*` | Generated locally | Pipeline smoke testing |
| Smoke | `smoke_*` | Generated locally | Automated test cleanup |
| Public external | `external_*` | Downloaded public datasets | Pipeline evaluation |
| Real lab | `lab_*` | Real microscope captures | Authentication development |

These must never be mixed. Each has its own dataset version prefix.
