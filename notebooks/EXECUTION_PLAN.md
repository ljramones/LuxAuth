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

### 8. 08-label-strategy-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Implemented (Phase 7) |
| **Purpose** | Compare species vs external_item_id label strategies for learned models |
| **Backend required** | Yes (for training); No (for inspecting results) |
| **Generated results needed** | `experiments/outputs/label-strategy-comparison/label_strategy_comparison_summary.json` |
| **Heavy compute** | Yes for training; No for inspection |
| **Strategies compared** | external_item_id (16 classes), species (4 classes) |
| **Prerequisite** | Loss-function comparison results (notebook 04) |

To generate results: `make label-strategy-comparison-leadata-quick` (fast) or
`make label-strategy-comparison-leadata-medium` from `auth-platform/`.

---

### 9. 05-backbone-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Implemented (Phase 8) |
| **Purpose** | Compare backbones, frozen vs fine-tuned, and embedding dimensions |
| **Backend required** | Yes (for training); No (for inspecting results) |
| **Generated results needed** | `experiments/outputs/backbone-comparison/backbone_comparison_summary.json` |
| **Heavy compute** | Yes for training (8 configs); No for inspection |
| **Configs** | ResNet18/50 × frozen/finetune × 256d/512d × contrastive/batch-hard |
| **Prerequisite** | Label-strategy comparison results (notebook 08) |

To generate results: `make backbone-comparison-leadata-quick` (fast) or
`make backbone-comparison-leadata-medium` from `auth-platform/`.

---

### 10. 09-augmentation-schedule-comparison.ipynb

| Field | Value |
|---|---|
| **Status** | Implemented (Phase 9) |
| **Purpose** | Compare augmentation profiles, optimizers, schedulers, and projection heads |
| **Backend required** | Yes (for training); No (for inspecting results) |
| **Generated results needed** | `experiments/outputs/augmentation-schedule-comparison/augmentation_schedule_comparison_summary.json` |
| **Heavy compute** | Yes for training (8 configs); No for inspection |
| **Fixed variables** | ResNet18 fine-tuned, 256d, external_item_id, LeaData V1 |
| **Prerequisite** | Backbone comparison results (notebook 05) |

To generate results: `make augmentation-schedule-comparison-leadata-quick` (fast) or
`make augmentation-schedule-comparison-leadata-medium` from `auth-platform/`.

---

### 11. 10-few-shot-prototype-matching.ipynb

| Field | Value |
|---|---|
| **Status** | **Phase 10 complete** — full grid executed against LeaData and FabricNET; results documented |
| **Purpose** | Compare few-shot inference strategies (NN, top-k mean, prototype centroid/medoid, abstention) across embedding models (texture_baseline, learned_metric, DINOv2 frozen) on LeaData; measure support-set stabilization curves |
| **Backend required** | Yes (Postgres + pgvector with embeddings persisted under each model version) |
| **Generated results needed** | `experiments/outputs/few-shot/<timestamp>/few_shot_summary.json` (and CSVs alongside) |
| **Heavy compute** | Medium — DINOv2 weights download once (~350MB); 500 episodes per cell; full grid runs in tens of minutes |
| **Strategies compared** | nearest_neighbor, top_k_mean, prototype_centroid, prototype_medoid, prototype_centroid_with_abstention |
| **Prerequisite** | DINOv2 embeddings persisted via `make generate-dinov2-embeddings` |
| **Diagnostic-only caveat** | LeaData species/item labels are not authentic-vs-counterfeit; do not extrapolate K values directly to luxury authentication |
| **Curated results** | [Few-Shot Prototype Matching Results](../docs/datasets/few-shot-prototype-results.md) |

To regenerate results: `make few-shot-quick` (smoke), `make few-shot-full-leadata-itemid`,
`make few-shot-full-leadata-species`, or `make few-shot-full-leadata-ood` from `auth-platform/`.
Cross-tabulate runs with `make compare-few-shot`.

**Phase 10c (PatchCore anomaly detection)** is **deferred-pending-shadow-evidence**. Phase 10 evidence + external review reframed PatchCore from "planned parallel track" to "scheduled when at least one trigger condition is met" — typically when shadow-period real-capture data surfaces a class of failure the metric path cannot resolve. Trigger conditions are listed in [DINOv2 Shadow Integration Plan §12](../docs/roadmaps/dinov2-shadow-integration-plan.md#12-patchcore-relationship-phase-10c).

**Phase 11 (DINOv2 Shadow Integration)** is the production-bound follow-on. It introduces DINOv2 as a `shadow_candidate` path running alongside the production decision authority during a bounded evidence-gathering window. The production decision authority remains `texture_baseline_v0.2.0` for the entire shadow period — running the empirically-weaker model in production while gathering evidence on the candidate is a deliberate conservative choice. Sub-phases 11A through 11F cover model registry, candidate threshold profile, reference re-embedding, workbench query support, dual-strategy shadow logging, real-capture recalibration, and promotion decision review. Promotion is gated on pre-declared criteria (4 weeks calendar, 100+ sessions, expert-reviewed divergence subset, recalibrated thresholds, strategy selection from real-data evidence). Full plan: [DINOv2 Shadow Integration Plan](../docs/roadmaps/dinov2-shadow-integration-plan.md).

---

### 12. 99-experiment-summary-template.ipynb

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
