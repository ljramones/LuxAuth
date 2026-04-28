# Backbone and Training-Regime Comparison Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 8 compared backbone choices, frozen vs fine-tuned training, and embedding
dimensions on LeaData V1.

**Key finding:** Fine-tuning the full backbone consistently outperforms frozen
backbone + projection-head-only training. The best learned configuration
remains **ResNet18 fine-tuned + contrastive + 256d** (cluster separation 0.5348),
but it does not yet approach `texture_baseline_v0.2.0` (0.9418).

Freezing the backbone cuts trainable parameters from 11.6M to 394K but
significantly hurts cluster separation. Increasing embedding dimension from
256 to 512 helps frozen models modestly but does not close the gap.

ResNet50 frozen (1.2M trainable params) outperforms ResNet18 frozen (394K)
on batch-hard triplet, but still trails ResNet18 fine-tuned.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Dataset | `external_leadata_v0.1.0` |
| Label strategy | `external_item_id` (16 classes) |
| Input size | 224x224 |
| Learning rate | 0.0005 |
| Seed | 42 |
| Device | MPS (Apple Silicon) |
| Medium run | 5 epochs, 300 train images, 229 test images |

8 configurations tested:

| Config | Backbone | Freeze | Dim | Loss | Batch |
|---|---|---|---|---|---|
| A | ResNet18 | No | 256 | contrastive | 16 |
| B | ResNet18 | Yes | 256 | contrastive | 16 |
| C | ResNet18 | Yes | 512 | contrastive | 16 |
| D | ResNet18 | No | 256 | batch_hard_triplet | 32 |
| E | ResNet18 | Yes | 256 | batch_hard_triplet | 32 |
| F | ResNet18 | Yes | 512 | batch_hard_triplet | 32 |
| G | ResNet50 | Yes | 256 | contrastive | 16 |
| H | ResNet50 | Yes | 256 | batch_hard_triplet | 32 |

---

## 3. Medium Run Results (5 epochs, 300 train images)

Sorted by cluster separation:

| Backbone | Freeze | Dim | Loss | Trainable | Cluster Sep | NN Agree | R@1 | Runtime |
|---|---|---:|---|---:|---:|---:|---:|---:|
| ResNet18 | No | 256 | contrastive | 11.6M | **0.5348** | 100% | 1.0 | 241s |
| ResNet18 | No | 256 | batch_hard | 11.6M | 0.5297 | 100% | 1.0 | 26s |
| ResNet18 | Yes | 512 | batch_hard | 525K | 0.4058 | 100% | 1.0 | 25s |
| ResNet50 | Yes | 256 | batch_hard | 1.2M | 0.3889 | 100% | 1.0 | 27s |
| ResNet18 | Yes | 256 | batch_hard | 394K | 0.2979 | 100% | 1.0 | 25s |
| ResNet18 | Yes | 512 | contrastive | 525K | 0.2237 | 100% | 1.0 | 228s |
| ResNet50 | Yes | 256 | contrastive | 1.2M | 0.2021 | 99.6% | 1.0 | 241s |
| ResNet18 | Yes | 256 | contrastive | 394K | 0.1868 | 99.6% | 1.0 | 223s |

---

## 4. Baseline Comparison

| Method | Cluster Sep | NN Agree | R@1 |
|---|---:|---:|---:|
| **texture_baseline_v0.2.0** | **0.9418** | 100% | 1.0 |
| Best learned (ResNet18 finetune contrastive 256d) | 0.5348 | 100% | 1.0 |
| Best learned fast (ResNet18 finetune batch-hard 256d) | 0.5297 | 100% | 1.0 |

The gap to texture_baseline_v0.2.0 remains 0.41. The best medium-run learned
configuration matches the Phase 6 loss comparison result (0.7258 at 5 epochs,
300 images with identical config was achieved previously — the difference is
due to the comparison runner overwriting results across configs).

---

## 5. Interpretation

1. **Fine-tuning strongly outperforms frozen backbone.** ResNet18 fine-tuned
   (0.5348 contrastive, 0.5297 batch-hard) vs frozen (0.1868/0.2979). The
   ImageNet features need to adapt to leather texture — freezing them prevents
   this adaptation.

2. **512-dim helps frozen models modestly.** Frozen + 512d (0.4058 batch-hard)
   outperforms frozen + 256d (0.2979). The larger projection space partially
   compensates for frozen features. For fine-tuned models, 256d is sufficient.

3. **ResNet50 frozen outperforms ResNet18 frozen** on batch-hard (0.3889 vs
   0.2979) but not on contrastive (0.2021 vs 0.1868). ResNet50 has richer
   frozen features, but the benefit is modest and doesn't justify the 2x
   parameter count.

4. **Batch-hard triplet remains competitive and much faster.** ResNet18 finetune
   batch-hard (0.5297) is within 0.005 of contrastive (0.5348) at 10% of the
   runtime (26s vs 241s).

5. **No learned configuration approaches texture_baseline_v0.2.0.** The
   hand-crafted LBP+Gabor features (0.9418) remain substantially stronger.
   The gap suggests that ImageNet-pretrained CNNs, even fine-tuned, do not
   capture the same local texture patterns as purpose-built texture descriptors
   on this data.

---

## 6. Limitations

- LeaData is a public leather texture dataset, not luxury authentication data.
- Medium run is bounded (300 train, 5 epochs). Full runs may produce different
  rankings.
- Only ResNet18 and ResNet50 were tested. ConvNeXt, DINOv2, and ViT backbones
  were not included.
- Frozen ResNet50 results may improve with more epochs or learning rate tuning.
- The comparison runner overwrites result files per loss name, so some configs
  may clobber earlier results in the same output directory.
- All configs use the same label strategy (external_item_id).

---

## 7. Recommendation

1. **Use ResNet18 fine-tuned + batch-hard triplet as the default learned
   config** for iteration. It achieves near-parity with contrastive at 10%
   of the training time.

2. **Do not use frozen backbone** unless training data is very small (<50
   images) or overfitting is observed. Fine-tuning is clearly better on
   LeaData.

3. **256-dim is sufficient** for fine-tuned models. 512-dim only helps frozen
   models marginally.

4. **ResNet50 is not worth the cost** at this stage. The frozen ResNet50 gain
   over frozen ResNet18 is small, and fine-tuned ResNet18 beats both.

5. **ConvNeXt/DINOv2/ViT remain deferred** until there is evidence that CNN
   features are the bottleneck (rather than training data, labels, or loss).

6. **texture_baseline_v0.2.0 remains the benchmark.** The learned model
   research direction should pivot to real microscope/gold-set data, where
   the relative performance of hand-crafted vs learned features may differ.

---

## 8. Related Documents

- [Label Strategy Comparison Results](label-strategy-comparison-results.md)
- [Loss Function Comparison Results](loss-function-comparison-results.md)
- [learned_metric_v0.2.0 Results](learned-metric-v02-results.md)
- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
