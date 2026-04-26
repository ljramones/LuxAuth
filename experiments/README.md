# Experiments

Structured experiment configurations and outputs for LuxAuth ML research.

## Structure

```text
experiments/
├── configs/          Experiment configuration YAML files
├── outputs/          Generated outputs (gitignored)
└── reports/          Generated reports (gitignored)
```

## Usage

1. Define experiment config in `configs/`
2. Run experiment from `notebooks/` or CLI
3. Outputs saved to `outputs/{experiment_id}/`
4. Curated summaries copied to `docs/datasets/results/` if worth preserving

## Rules

- `outputs/` and `reports/` are gitignored — regenerable artifacts only
- Config files are committed — they define reproducible experiments
- Never commit model weights, embeddings, or dataset images here
