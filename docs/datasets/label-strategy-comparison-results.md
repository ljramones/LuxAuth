# Label Strategy Comparison Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 7 compared label strategies for learned metric models on LeaData V1.
Two strategies were tested with two losses each:

- **external_item_id** (16 sample groups): finer-grained, sample-specific labels
- **species** (4 classes: Buffalo, Cow, Goat, Sheep): broader material-class labels

**Key finding:** `external_item_id` consistently outperforms `species` on cluster
separation and retrieval metrics across both losses. This is counterintuitive —
broader labels were expected to produce better-organized embedding spaces — but
makes sense because the finer labels provide a stronger and more diverse training
signal (16 distinct groups vs 4).

Species-level training with contrastive loss at 5 epochs / 300 images actually
produced lower cluster separation (0.1501) than at 2 epochs / 100 images (0.1964),
suggesting potential overfitting or a learning rate issue at this scale.

`texture_baseline_v0.2.0` (0.9418) remains substantially stronger than all
learned variants.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Dataset | `external_leadata_v0.1.0` |
| Backbone | ResNet18 (ImageNet pretrained) |
| Embedding dimension | 256 |
| Input size | 224x224 |
| Learning rate | 0.0005 |
| Seed | 42 |
| Device | MPS (Apple Silicon) |

| Config | Loss | Label strategy | Classes | Batch size |
|---|---|---|---|---|
| contrastive_external_item_id | contrastive | external_item_id | 16 | 16 |
| contrastive_species | contrastive | species | 4 | 16 |
| batch_hard_external_item_id | batch_hard_triplet | external_item_id | 16 | 32 |
| batch_hard_species | batch_hard_triplet | species | 4 | 32 |

**Semantic meaning:**
- `external_item_id` evaluation: "Does the model retrieve same sample group/item?"
- `species` evaluation: "Does the model retrieve same-species leather?"

These measure different tasks — direct comparison requires interpretation.

---

## 3. Quick Run Results (2 epochs, 100 train images)

| Loss | Label strategy | Classes | Cluster Sep | NN Agree | R@1 | Runtime |
|---|---|---:|---:|---:|---:|---:|
| contrastive | external_item_id | 16 | **0.5314** | 100% | 1.000 | 38s |
| contrastive | species | 4 | 0.1964 | 96.0% | 0.960 | 39s |
| batch_hard_triplet | external_item_id | 16 | 0.3169 | 100% | 1.000 | 5s |
| batch_hard_triplet | species | 4 | 0.1431 | 99.0% | 0.990 | 5s |

---

## 4. Medium Run Results (5 epochs, 300 train images)

| Loss | Label strategy | Classes | Cluster Sep | NN Agree | R@1 | R@3 | Runtime |
|---|---|---:|---:|---:|---:|---:|---:|
| contrastive | external_item_id | 16 | **0.7258** | 100% | 1.000 | 1.000 | 232s |
| contrastive | species | 4 | 0.1501 | 96.1% | 0.961 | 0.974 | 235s |
| batch_hard_triplet | external_item_id | 16 | 0.7127 | 100% | 1.000 | 1.000 | 25s |
| batch_hard_triplet | species | 4 | 0.3507 | 100% | 1.000 | 1.000 | 25s |

---

## 5. Baseline Comparison

| Method | Cluster Sep | NN Agree | R@1 |
|---|---:|---:|---:|
| **texture_baseline_v0.2.0** | **0.9418** | 100% | 1.0 |
| contrastive + external_item_id (medium) | 0.7258 | 100% | 1.0 |
| batch_hard + external_item_id (medium) | 0.7127 | 100% | 1.0 |
| batch_hard + species (medium) | 0.3507 | 100% | 1.0 |
| contrastive + species (medium) | 0.1501 | 96.1% | 0.961 |

---

## 6. Interpretation

1. **external_item_id consistently outperforms species** across both losses.
   With 16 classes vs 4, the model has a richer training signal — more distinct
   groups to separate, more negative pairs to learn from.

2. **Species labels produce weaker embeddings** because 4 classes provide less
   discrimination pressure. The model can satisfy the species objective without
   learning fine texture differences. For luxury authentication, this suggests
   finer-grained labels (per physical item, per region) will be more effective
   than broad category labels.

3. **Contrastive + species actually degraded** from quick to medium run (0.1964 →
   0.1501), suggesting overfitting or that longer contrastive pair training on
   only 4 classes collapses the embedding space. Batch-hard + species improved
   (0.1431 → 0.3507), indicating batch-hard mining is more robust on few-class
   problems.

4. **Batch-hard triplet remains competitive and much faster** (~25s vs ~232s).
   It also shows more stable behavior on the species strategy.

5. **No learned variant approaches texture_baseline_v0.2.0** (0.9418). The gap
   is 0.22 for the best learned configuration. Hand-crafted LBP+Gabor features
   remain purpose-built for local texture pattern extraction and outperform
   generic pretrained CNN features on this data.

6. **For future luxury gold-set data**, the label strategy must align with the
   authentication task: authenticity labels per physical item, with leakage
   prevention by item_id. external_item_id is the closest proxy available
   on LeaData.

---

## 7. Limitations

- LeaData is a public leather texture dataset, not luxury authentication data.
- Species labels are not authentic/fake labels.
- external_item_id labels may encourage sample-group memorization.
- Medium run is still bounded (300 train images, 5 epochs).
- Cluster separation and NN agreement are diagnostic metrics, not authentication accuracy.
- Only ResNet18 was tested. Larger backbones may change the ranking.
- Species labels may perform better with more epochs, larger batch sizes, or
  learning rate tuning — this was not exhaustively explored.

---

## 8. Recommendation

1. **Use `external_item_id` as the default label strategy** for learned metric
   experiments. It produces the best embedding quality on this data.

2. **Use `species` only when testing broader material-class retrieval** as a
   separate semantic task.

3. **For future luxury gold-set data**, label strategy should be:
   - `authenticity_status` for authentic-vs-counterfeit discrimination
   - `reference_item_id` for item-level grouping and leakage prevention
   - `region_code` for region-specific model experiments

4. **Next learned experiment** should try frozen-backbone + projection-head-only
   training, or a different embedding dimension, before changing the backbone.
   The label strategy question is now answered for public texture data.

5. **Do not change backend default model.** `texture_baseline_v0.2.0` remains
   the strongest method.

---

## 9. Related Documents

- [Loss Function Comparison Results](loss-function-comparison-results.md)
- [learned_metric_v0.2.0 Results](learned-metric-v02-results.md)
- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
