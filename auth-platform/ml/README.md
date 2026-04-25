# Metric Learning Training

Local CPU-friendly PyTorch metric-learning training pipeline.

**This is NOT production authentication.** It is a local prototype that validates
the ML lifecycle: dataset → training → model artifact → embedding → evaluation.

## Usage

```bash
# From auth-platform root:
make train-metric-model
make reembed-reference-data MODEL=learned_metric_v0.1.0
make run-evaluation MODEL=learned_metric_v0.1.0
make compare-evaluations
```

## Model: learned_metric_v0.1.0

- Architecture: ResNet18 backbone + 128-dim projection head
- Loss: Contrastive loss (positive/negative pairs)
- Input: 224x224 RGB (resized from 512x512 normalized images)
- Output: 128-dim unit-normalized embedding
- Training: CPU, synthetic data only
