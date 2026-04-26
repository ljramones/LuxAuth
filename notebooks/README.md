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
| 99-experiment-summary-template | Template for recording experiment conclusions |

## Rules

- Start from governed dataset versions
- Never split by image when physical item IDs exist
- Never mix synthetic/public/lab data without explicit purpose
- Never treat public datasets as authentication proof
- Record config and random seed
- Save outputs under `experiments/outputs/`
- Curated summaries go to `docs/datasets/results/`

## Setup

```bash
cd auth-platform
source .venv/bin/activate  # or create a notebook venv
pip install jupyter
jupyter notebook --notebook-dir=../notebooks
```
