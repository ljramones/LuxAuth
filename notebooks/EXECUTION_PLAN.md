# Notebook Execution Plan

Recommended order, status, and expectations for each experiment notebook.

---

## Quick Start

```bash
make backend-up         # start backend (Postgres, LocalStack, services)
make notebook-deps      # install notebook dependencies
make notebook-kernel    # register Jupyter kernel
make notebook           # start JupyterLab
```

In Jupyter: **Kernel > Change Kernel > LuxAuth auth-platform**

---

## Run Order for a Fresh Clone

1. Start with **00-dataset-inspection** to verify DB access and dataset state.
2. Run completed-result notebooks (01, 02, 06, 07, 03) to inspect existing
   experiment outputs.
3. Do not run future/heavy notebooks (04, 05) unless explicitly implementing
   that experiment phase.
4. Use **99-experiment-summary-template** when writing up new experiment results.

---

## Notebook Status and Details

### 1. 00-dataset-inspection.ipynb

| Field | Value |
|---|---|
| **Status** | Ready |
| **Purpose** | Validate DB access, inspect datasets, splits, labels, regions, embedding coverage |
| **Backend required** | Yes (Postgres) |
| **Generated results needed** | None |
| **Heavy compute** | No |
| **Expected outputs** | FabricNET and LeaData datasets visible; split counts; v0.2.0 coverage where persisted |
| **What to look for** | Datasets load correctly; split sizes match expectations; no unexpected gaps |

---

### 2. 01-preprocessing-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Backed by completed Phase 2 results |
| **Purpose** | Inspect preprocessing comparison metrics across strategies |
| **Backend required** | No (loads generated JSON) |
| **Generated results needed** | `experiments/outputs/preprocessing-comparison/*__preprocessing_metrics.json` |
| **Heavy compute** | No by default; loads pre-generated metrics |
| **Expected outputs** | Strategy comparison table; cluster separation and NN agreement bar charts |
| **What to look for** | CLAHE consistently best cluster separation; all strategies 100% NN agreement |
| **Related doc** | [Preprocessing Comparison Results](../docs/datasets/preprocessing-comparison-results.md) |

To regenerate results: `make preprocessing-experiment-fabricnet` and
`make preprocessing-experiment-leadata-medium` from `auth-platform/`.

---

### 3. 02-baseline-embedding-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Backed by completed Phase 1 results |
| **Purpose** | Compare texture_baseline_v0.1.0 vs v0.2.0 embedding quality |
| **Backend required** | No (loads generated JSON) |
| **Generated results needed** | `experiments/outputs/baseline-feature-comparison/*__record.json` |
| **Heavy compute** | No |
| **Expected outputs** | Feature extractor comparison table |
| **What to look for** | v0.2.0 (LBP+Gabor, 256-dim) improves cluster separation over v0.1.0 (128-dim) |
| **Related doc** | [Baseline Feature Comparison Results](../docs/datasets/baseline-feature-comparison-results.md) |

To regenerate: `make baseline-feature-experiment-fabricnet` and
`make baseline-feature-experiment-leadata` from `auth-platform/`.

---

### 4. 06-region-specific-analysis.ipynb

| Field | Value |
|---|---|
| **Status** | Backed by completed Phase 3 results |
| **Purpose** | Inspect per-region coverage, readiness, and embedding diagnostics |
| **Backend required** | No (loads generated JSON) |
| **Generated results needed** | `experiments/outputs/region-analysis/*__region_analysis.json` |
| **Heavy compute** | No |
| **Expected outputs** | Coverage table; readiness distribution; images-per-region chart; cluster separation by region |
| **What to look for** | External regions flagged; readiness levels match image counts; no unknown regions |
| **Related doc** | [Region-Specific Analysis Results](../docs/datasets/region-specific-analysis-results.md) |

To regenerate: `make region-analysis-fabricnet` and `make region-analysis-leadata`
from `auth-platform/`.

---

### 5. 07-ood-and-query-scoring.ipynb

| Field | Value |
|---|---|
| **Status** | Backed by completed Phase 4 results |
| **Purpose** | Inspect OOD scoring method comparison and ID/OOD distributions |
| **Backend required** | No (loads generated JSON/CSV) |
| **Generated results needed** | `experiments/outputs/ood/*__ood_summary.json` and `*__ood_scores.csv` |
| **Heavy compute** | No |
| **Expected outputs** | Method comparison table; AUROC bar chart; ID vs OOD histograms |
| **What to look for** | FabricNET-as-ID achieves near-perfect separation; LeaData-as-ID shows overlap |
| **Related doc** | [OOD Experiment Results](../docs/datasets/ood-experiment-results.md) |

To regenerate: `make ood-experiment-fabricnet-vs-leadata` and
`make ood-experiment-leadata-vs-fabricnet` from `auth-platform/`.

---

### 6. 03-metric-learning-experiments.ipynb

| Field | Value |
|---|---|
| **Status** | Backed by completed Phase 5 initial result |
| **Purpose** | Inspect learned model training/evaluation and compare against texture baseline |
| **Backend required** | No (loads generated JSON) |
| **Generated results needed** | `experiments/outputs/learned-metric/*__experiment_record.json` and `*__training_metrics.json` |
| **Heavy compute** | No (inspection only); training requires `make learned-metric-experiment-leadata-v02` |
| **Expected outputs** | Training loss curve; learned vs baseline comparison table |
| **What to look for** | Learned model achieves 100% NN agreement but lower cluster separation than v0.2.0 baseline |
| **Related doc** | [learned_metric_v0.2.0 Results](../docs/datasets/learned-metric-v02-results.md) |

To regenerate (slow, ~42 min): `make learned-metric-experiment-leadata-v02`
from `auth-platform/`. Quick version (~44s): `make learned-metric-experiment-leadata-quick`.

---

### 7. 04-loss-function-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Implemented (Phase 6) |
| **Purpose** | Compare loss functions while holding dataset, backbone, and preprocessing constant |
| **Backend required** | Yes (for training); No (for inspecting results) |
| **Generated results needed** | `experiments/outputs/loss-comparison/loss_comparison_summary.json` |
| **Heavy compute** | Yes for training; No for inspection |
| **Losses compared** | Contrastive, supervised contrastive (SupCon), batch-hard triplet |
| **Prerequisite** | Phase 5 learned_metric_v0.2.0 baseline established |

To generate results: `make loss-comparison-leadata-quick` (fast) or
`make loss-comparison-leadata` (full) from `auth-platform/`.

---

### 8. 05-backbone-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Future |
| **Purpose** | Compare backbone architectures after loss-function comparison |
| **Backend required** | Yes (when implemented) |
| **Heavy compute** | Yes (multiple training runs) |
| **Candidate backbones** | ResNet18, ResNet50, ConvNeXt-Tiny, ViT/SigLIP/DINOv2-style encoders |
| **Prerequisite** | Loss-function comparison results (notebook 04) |

Do not run until the backbone experiment framework is implemented.

---

### 9. 99-experiment-summary-template.ipynb

| Field | Value |
|---|---|
| **Status** | Template |
| **Purpose** | Create curated experiment summaries for new experiments |
| **Backend required** | No |
| **Heavy compute** | No |

Use this template when writing up results from a new experiment phase.

---

## Do Not Commit

- Notebook execution outputs (clear before committing)
- Generated chart images (`notebooks/_*.png`)
- `experiments/outputs/*`
- `experiments/reports/*`
- Model artifacts (`.pt`, `.pth`, `.onnx`)
- Dataset files (`datasets/external/*`)

To clear notebook outputs before committing:

```bash
cd auth-platform
.venv/bin/jupyter nbconvert --clear-output --inplace ../notebooks/*.ipynb
```

---

## Troubleshooting

See [SETUP.md](SETUP.md) for environment setup and common issues.
