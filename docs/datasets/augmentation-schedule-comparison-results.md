# Augmentation and Training Schedule Comparison Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 9 compared augmentation profiles, optimizers, schedulers, projection heads,
and epoch counts while holding the backbone (ResNet18 fine-tuned), embedding
dimension (256), and label strategy (external_item_id) fixed.

**Key findings:**
- **Medium augmentation with batch-hard triplet at 5 epochs** (0.7127) is the
  best fast configuration — same result as Phase 6.
- **Cosine LR scheduling at 10 epochs** (0.6589) outperforms flat LR at 10
  epochs (0.5583), but still trails the 5-epoch baseline.
- **Strong augmentation hurts** at 5 epochs (0.3506), likely because aggressive
  transforms with limited training time prevent convergence.
- **Light augmentation underperforms medium** (0.4028 vs 0.7127).
- **AdamW with weight decay** (0.5400) does not improve over Adam (0.5583) at
  10 epochs.
- **Contrastive control** (0.7258) remains slightly better than batch-hard
  (0.7127) but at 9x the training time.
- **No configuration approaches texture_baseline_v0.2.0** (0.9418).

The gap (0.22) between the best learned configuration and the hand-crafted
baseline has not narrowed further from Phase 6/8. Training-regime tweaks are
producing diminishing returns on public texture data.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Dataset | `external_leadata_v0.1.0` |
| Backbone | ResNet18 (ImageNet pretrained, fine-tuned) |
| Embedding dimension | 256 |
| Label strategy | `external_item_id` (16 classes) |
| Input size | 224x224 |
| Seed | 42 |
| Device | MPS (Apple Silicon) |
| Medium run | 300 train images, config-specified epochs |

| Config | Aug | Loss | Opt | Scheduler | Epochs | Proj head |
|---|---|---|---|---|---|---|
| A | light | batch_hard | adam | none | 5 | 256 |
| B | medium | batch_hard | adam | none | 5 | 256 |
| C | strong | batch_hard | adam | none | 5 | 256 |
| D | medium | batch_hard | adam | none | 10 | 256 |
| E | medium | batch_hard | adamw | none | 10 | 256 |
| F | medium | batch_hard | adam | cosine | 10 | 256 |
| G | medium | batch_hard | adam | none | 10 | 512 |
| H | medium | contrastive | adam | none | 5 | 256 |

---

## 3. Medium Run Results (300 train images)

Sorted by cluster separation:

| Aug | Loss | Opt | Sched | Ep | Cluster Sep | NN Agree | R@1 | Runtime |
|---|---|---|---|---:|---:|---:|---:|---:|
| medium | contrastive | adam | none | 5 | **0.7258** | 100% | 1.0 | 233s |
| medium | batch_hard | adam | none | 5 | 0.7127 | 100% | 1.0 | 26s |
| medium | batch_hard | adam | cosine | 10 | 0.6589 | 100% | 1.0 | 51s |
| medium | batch_hard | adam | none | 10 | 0.5583 | 100% | 1.0 | 51s |
| medium | batch_hard | adamw | none | 10 | 0.5400 | 100% | 1.0 | 51s |
| light | batch_hard | adam | none | 5 | 0.4028 | 100% | 1.0 | 25s |
| strong | batch_hard | adam | none | 5 | 0.3506 | 99.6% | 1.0 | 27s |
| medium | batch_hard | adam | none | 10 | 0.3038 | 100% | 1.0 | 51s |

**Note:** Two configs with medium/batch_hard/adam/none/10ep produced different
results (0.5583 and 0.3038) because the projection head config (256 vs 512)
creates different models. The 512-dim head (0.3038) underperformed, consistent
with the Phase 8 finding that 512-dim doesn't help fine-tuned ResNet18.

---

## 4. Baseline Comparison

| Method | Cluster Sep | NN Agree | R@1 |
|---|---:|---:|---:|
| **texture_baseline_v0.2.0** | **0.9418** | 100% | 1.0 |
| Best learned (contrastive medium 5ep) | 0.7258 | 100% | 1.0 |
| Best fast (batch_hard medium 5ep) | 0.7127 | 100% | 1.0 |

---

## 5. Interpretation

1. **Medium augmentation is the sweet spot.** Light is too weak (0.4028),
   strong is too aggressive (0.3506), medium is optimal (0.7127).

2. **More epochs do not help with flat LR.** 10 epochs (0.5583) is worse than
   5 epochs (0.7127), suggesting overfitting on the 300-image training set.

3. **Cosine scheduling partially rescues longer training.** 10 epochs with
   cosine (0.6589) outperforms flat (0.5583), but still doesn't beat 5-epoch
   medium (0.7127). The learning rate likely needs to be higher initially and
   decay more aggressively.

4. **AdamW doesn't help.** Weight decay (0.5400) performs similarly to Adam
   (0.5583) at 10 epochs. The regularization is not the bottleneck.

5. **Larger projection head (512) hurts.** 0.3038 vs 0.5583 at same epoch
   count. Extra capacity without extra data leads to worse generalization.

6. **Training-regime tweaks show diminishing returns.** The best learned
   configuration (0.7258 contrastive / 0.7127 batch-hard) has not improved
   across Phases 6, 8, and 9. The gap to texture_baseline_v0.2.0 (0.22)
   appears to be a fundamental limitation of pretrained ResNet18 features
   fine-tuned on 300 leather texture images.

---

## 6. Limitations

- LeaData is public leather texture data, not luxury authentication data.
- Medium run is bounded (300 train images).
- Not all hyperparameter combinations were tested.
- Microscopy-aware augmentations were not implemented yet.
- The 0.22 gap to texture_baseline_v0.2.0 may narrow on larger/different data.
- No real microscope/gold-set data was used.

---

## 7. Recommendation

1. **Use medium augmentation + batch-hard triplet + Adam + 5 epochs** as the
   standard learned training recipe. It achieves the best fast result.

2. **Stop further training-regime experiments on LeaData.** Diminishing returns
   suggest the bottleneck is the data/feature gap, not training configuration.

3. **Pivot to real microscope/gold-set data** for the next learned-model
   experiment. The public texture diagnostic phase has answered the key
   questions: loss function, label strategy, backbone, freeze/finetune,
   augmentation, optimizer, scheduler, and projection head.

4. **Keep texture_baseline_v0.2.0 as backend default.** Hand-crafted LBP+Gabor
   features remain substantially stronger on public texture data.

5. **Re-evaluate learned models on real microscope data** when available. The
   relative performance of hand-crafted vs learned features may differ on
   real luxury item textures at microscope magnification.

---

## 8. Related Documents

- [Backbone Comparison Results](backbone-comparison-results.md)
- [Loss Function Comparison Results](loss-function-comparison-results.md)
- [Label Strategy Comparison Results](label-strategy-comparison-results.md)
- [learned_metric_v0.2.0 Results](learned-metric-v02-results.md)
- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
