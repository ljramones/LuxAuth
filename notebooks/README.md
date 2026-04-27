# Experiment Notebooks

Jupyter notebooks for exploring LuxAuth ML strategies.

## Notebooks

| Notebook | Purpose |
|---|---|
| 00-dataset-inspection | Inspect dataset structure, splits, labels, coverage |
| 01-preprocessing-comparison | Compare center-crop vs padded-resize vs multi-crop |
| 02-baseline-embedding-comparison | Compare texture_baseline variants (histogram, LBP, Gabor) |
| 03-metric-learning-experiments | Train and evaluate learned metric models |
| 04-loss-function-comparison | Compare contrastive, triplet, ArcFace, SupCon losses |
| 05-backbone-comparison | Compare ResNet, ConvNeXt, ViT, DINOv2 backbones |
| 06-region-specific-analysis | Per-region embedding behavior and scoring |
| 07-ood-and-query-scoring | OOD scoring method comparison |
| 99-experiment-summary-template | Template for recording experiment conclusions |

## Rules

- Start from governed dataset versions
- Never split by image when physical item IDs exist
- Never mix synthetic/public/lab data without explicit purpose
- Never treat public datasets as authentication proof
- Record config and random seed
- Save outputs under `experiments/outputs/`
- Curated summaries go to `docs/datasets/results/`

## Before Running Notebooks

See [SETUP.md](SETUP.md) for full setup instructions, kernel registration, and
troubleshooting.

Quick start from repo root:

```bash
make notebook-deps      # install dependencies
make notebook-kernel    # register Jupyter kernel
make notebook           # start JupyterLab
```

Then select **Kernel > Change Kernel > LuxAuth auth-platform** in Jupyter.
