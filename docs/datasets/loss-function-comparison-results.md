# Loss Function Comparison Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 6 compared three metric learning loss functions on LeaData V1 while
holding backbone (pretrained ResNet18), embedding dimension (256), and
preprocessing constant.

**Medium run results (5 epochs, 300 train images, 229 test images):**

| Loss | Cluster Separation |
|---|---|
| contrastive | **0.7258** |
| batch_hard_triplet | 0.7127 |
| supervised_contrastive | 0.6483 |
| texture_baseline_v0.2.0 | **0.9418** |

All three learned losses improved substantially from the quick run (2 epochs,
100 images) to the medium run, confirming that the quick comparison
underestimated SupCon and batch-hard triplet due to insufficient training.

**Contrastive loss remains the strongest learned loss** on this data, followed
closely by batch-hard triplet. However, all learned losses still fall well
short of `texture_baseline_v0.2.0` (0.9418) on cluster separation. The gap
has narrowed — from 0.41 in the quick run to 0.22 in the medium run — but
hand-crafted LBP+Gabor features remain the best method for public leather
texture diagnostics.

These are public texture datasets. Results do **not** prove luxury
authentication accuracy.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Dataset | `external_leadata_v0.1.0` |
| Backbone | ResNet18 (ImageNet pretrained) |
| Embedding dimension | 256 |
| Label strategy | `external_item_id` (16 classes) |
| Input size | 224x224 |
| Learning rate | 0.0005 |
| Weight decay | 0.0001 |
| Seed | 42 |
| Device | MPS (Apple Silicon) |

| Loss | Batch size | Training mode |
|---|---|---|
| contrastive | 16 | Pair-based (generated pairs) |
| supervised_contrastive | 16 | Batch-based (labels in batch) |
| batch_hard_triplet | 32 | Batch-based (online mining) |

Baseline comparison target: `texture_baseline_v0.2.0` (256-dim, LBP+Gabor).

---

## 3. Quick Run Results (2 epochs, 100 train images)

| Loss | Limit | Epochs | Cluster Sep | NN Agree | R@1 | Runtime |
|---|---:|---:|---:|---:|---:|---:|
| contrastive | 100 | 2 | 0.5314 | 100% | 1.0 | 38s |
| batch_hard_triplet | 100 | 2 | 0.3169 | 100% | 1.0 | 8s |
| supervised_contrastive | 100 | 2 | 0.2117 | 100% | 1.0 | 5s |

Quick results underestimate SupCon and batch-hard triplet — both need more
epochs and data to converge. Contrastive loss benefits from pre-generated
pairs that provide balanced positive/negative sampling even at low epoch count.

---

## 4. Medium Run Results (5 epochs, 300 train images)

| Loss | Limit | Epochs | Cluster Sep | NN Agree | R@1 | R@3 | R@5 | Runtime |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| contrastive | 300 | 5 | **0.7258** | 100% | 1.0 | 1.0 | 1.0 | 239s |
| batch_hard_triplet | 300 | 5 | 0.7127 | 100% | 1.0 | 1.0 | 1.0 | 26s |
| supervised_contrastive | 300 | 5 | 0.6483 | 100% | 1.0 | 1.0 | 1.0 | 27s |

All losses improved substantially from the quick run. Contrastive and
batch-hard triplet are now within 0.02 of each other. SupCon trails by ~0.08
but showed the largest relative improvement (0.2117 → 0.6483, a 3× gain).

Validation loss for SupCon showed volatility (oscillating between 1.8–2.6),
suggesting the temperature or learning rate may need tuning for this dataset.

---

## 5. Baseline Comparison

| Method | Dim | Cluster Sep | NN Agree | R@1 |
|---|---:|---:|---:|---:|
| texture_baseline_v0.1.0 | 128 | 0.6730 | 100% | 1.0 |
| **texture_baseline_v0.2.0** | 256 | **0.9418** | 100% | 1.0 |
| learned contrastive (medium) | 256 | 0.7258 | 100% | 1.0 |
| learned batch_hard_triplet (medium) | 256 | 0.7127 | 100% | 1.0 |
| learned supervised_contrastive (medium) | 256 | 0.6483 | 100% | 1.0 |

The best learned loss (contrastive, 0.7258) now exceeds `texture_baseline_v0.1.0`
(0.6730) but remains well below `texture_baseline_v0.2.0` (0.9418). The gap
is 0.2160 — meaningful but narrowing.

---

## 6. Interpretation

**Contrastive remains the strongest learned loss** for this dataset/configuration,
but the margin over batch-hard triplet is small (0.013). Key observations:

1. **All losses are converging with more data and epochs.** The quick-to-medium
   improvement was large for all three, suggesting further training may continue
   to close the gap. However, the rate of improvement is likely to diminish.

2. **Batch-hard triplet is competitive and much faster.** At 26s vs 239s for
   contrastive, batch-hard triplet achieves nearly the same cluster separation
   in ~10% of the training time. The pair-generation overhead in contrastive
   training dominates runtime.

3. **SupCon needs more tuning.** Validation loss volatility and lower cluster
   separation suggest the temperature (0.07) or batch construction may not be
   optimal. SupCon typically benefits from larger batch sizes (64–256) and
   careful temperature tuning.

4. **All learned methods retrieve correctly** (100% NN agreement, perfect
   recall@K) but form less compact clusters than hand-crafted features. This
   pattern is consistent with the Phase 5 finding.

5. **The label strategy likely limits all learned methods.** `external_item_id`
   maps to 16 species/sample groups. With 300 training images across 16 classes,
   each class averages ~19 images. The model may be memorizing sample-specific
   texture patterns rather than learning generalizable texture discriminators.

6. **Texture baseline v0.2.0 remains substantially stronger** because LBP and
   Gabor features are purpose-built for local texture pattern extraction. A
   pretrained ResNet18 with generic ImageNet features may not capture the same
   fine-grained texture structure, even with metric learning fine-tuning.

---

## 7. Limitations

- LeaData is a public leather texture dataset, not luxury authentication data.
- `external_item_id` labels may encourage sample-group memorization rather than
  generalizable texture learning.
- Medium run is still bounded (300 train images, 5 epochs). Full-dataset runs
  with more epochs may produce different rankings.
- Cluster separation is a diagnostic metric, not authentication accuracy.
- The learned model uses ResNet18 only. Larger backbones were not tested in this
  phase.
- Contrastive pair generation is slower than batch-based methods, inflating its
  runtime. The pair sampler generates 3× the training images as pairs.
- SupCon temperature and batch size were not optimized.
- `texture_baseline_v0.2.0` remains substantially stronger for public texture
  diagnostics.

---

## 8. Recommendation

1. **Keep contrastive as the default learned loss** for now. It produces the
   best cluster separation and is well-understood.

2. **Consider batch-hard triplet as a practical alternative** for faster
   iteration. It achieves nearly the same quality in ~10% of the training time.

3. **Next experiment should test label strategy**, not loss function. Try species
   labels or frozen-backbone + projection-head-only training. The label strategy
   is more likely to be the bottleneck than the loss function.

4. **Do not move to ResNet50/ConvNeXt yet.** The label strategy and training
   setup questions should be answered first. A larger backbone is unlikely to
   help if the training signal is limited.

5. **SupCon may warrant a re-run** with larger batch size (32–64) and adjusted
   temperature if label strategy experiments show that batch-based losses are
   the right direction.

6. **Do not change backend default model.** `texture_baseline_v0.2.0` remains
   the strongest method on public texture data.

---

## 9. Related Documents

- [learned_metric_v0.2.0 Results](learned-metric-v02-results.md)
- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
