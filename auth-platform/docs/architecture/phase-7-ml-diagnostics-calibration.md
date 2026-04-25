# Phase 7: ML Diagnostics, Calibration, and Experiment Tracking

## Overview

Phase 7 adds tools to inspect, diagnose, and calibrate model behavior before
attempting serious model improvement. These tools make model behavior explainable
and help identify why a model underperforms before changing architecture or data.

## Why Diagnostics Before Tuning

The learned_metric_v0.1.0 model currently underperforms the hand-crafted baseline
on synthetic data. Before investing in model architecture changes:

1. **Inspect embedding distributions** — are authentic/counterfeit clusters separated?
2. **Check nearest-neighbor behavior** — do neighbors have correct labels?
3. **Sweep thresholds** — are current thresholds appropriate for the embedding space?
4. **Examine false negatives** — what similarity patterns cause misclassification?
5. **Visualize projections** — can we see the embedding space structure?

## Available Diagnostic Commands

| Command | Purpose |
|---|---|
| `make analyze-embeddings MODEL=...` | Embedding distribution statistics |
| `make inspect-neighbors MODEL=...` | Per-image nearest-neighbor analysis |
| `make calibrate-thresholds MODEL=...` | Threshold sweep and optimization |
| `make export-projection MODEL=...` | 2D PCA projection CSV for visualization |
| `make compare-evaluations` | Side-by-side model comparison |
| `make evaluation-report` | Detailed report with confusion matrix |

## Embedding Diagnostics

Reports:
- Embedding count, dimension, vector norms
- Pairwise cosine similarity statistics
- Intra-class vs inter-class similarity
- Cluster separation score
- Nearest-neighbor label agreement rate
- Per-region breakdown

## Threshold Calibration

Sweeps threshold combinations and reports:
- Best conservative profile (minimize false positives)
- Best balanced profile (maximize accuracy)
- Best zero-FP profile
- Use `--write-profile` to save a draft threshold profile

## Projection Export

Exports 2D PCA projections to CSV at `reports/projections/{dataset}/{model}/projection.csv`
for external visualization. No built-in UI — use any plotting tool.

## Training Configurability

| Option | Default | Description |
|---|---|---|
| `--model-version` | v0.1.0 | Version tag for the trained model |
| `--epochs` | 10 | Training epochs |
| `--lr` | 0.001 | Learning rate |
| `--batch-size` | 8 | Batch size |
| `--frozen-backbone` | false | Freeze ResNet backbone weights |
| `--pretrained` | false | Use ImageNet pretrained weights (requires internet) |
| `--no-augmentations` | false | Disable data augmentation |

## Multiple Model Versions

Each training run creates a distinct model version:
```bash
make train-metric-model MODEL_VERSION=learned_metric_v0.1.1
make reembed-reference-data MODEL=learned_metric_v0.1.1
make run-evaluation MODEL=learned_metric_v0.1.1
make compare-evaluations
```

## Disclaimers

- Diagnostics reveal model behavior on **synthetic** test data only
- Real product authentication requires real labeled datasets
- SageMaker remains deferred per ADR-0001
- These tools prepare for future model improvement, not current deployment
