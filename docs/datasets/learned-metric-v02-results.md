# learned_metric_v0.2.0 Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

`learned_metric_v0.2.0` is the first bounded learned metric experiment,
comparing a pretrained ResNet18 with contrastive loss against the hand-crafted
`texture_baseline_v0.2.0` on LeaData V1 public leather texture data.

**Key finding:** The learned model validates the training/evaluation pipeline
end-to-end but does **not** beat `texture_baseline_v0.2.0` on cluster
separation. Both achieve 100% NN agreement and perfect recall@K, but the
hand-crafted LBP+Gabor features produce substantially tighter clusters
(0.9418 vs 0.5609).

This is not surprising for a first experiment with generic contrastive loss on
a small public dataset. The result establishes a learned-model baseline and
identifies specific areas for improvement. It does **not** measure luxury
authentication accuracy — LeaData is a public leather texture dataset.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Dataset | `external_leadata_v0.1.0` |
| Backbone | ResNet18 (ImageNet pretrained) |
| Embedding dimension | 256 |
| Loss | Contrastive (margin=1.0) |
| Label strategy | `external_item_id` (16 classes) |
| Train split | 897 images |
| Validation split | 74 images |
| Test split | 229 images |
| Epochs | 20 |
| Batch size | 16 |
| Learning rate | 0.0005 |
| Weight decay | 0.0001 |
| Seed | 42 |
| Device | MPS (Apple Silicon) |
| Input size | 224x224 |
| Augmentations | Random resized crop, horizontal flip, rotation (15°), color jitter, random erasing (p=0.1) |

---

## 3. Training Summary

| Metric | Value |
|---|---|
| Training time | 2,520.7s (~42 minutes) |
| Final train loss | Converged |
| Final validation loss | Converged with some volatility |

Training converged within 20 epochs. Validation loss showed some volatility,
likely due to the small validation set (74 images) and contrastive pair
sampling randomness. The model did not diverge or collapse.

---

## 4. Results Table

| Method | Dim | Cluster Sep | NN Agree | R@1 | R@3 | R@5 |
|---|---|---|---|---|---|---|
| texture_baseline_v0.1.0 | 128 | 0.6730 | 100% | 1.0000 | 1.0000 | 1.0000 |
| **texture_baseline_v0.2.0** | 256 | **0.9418** | 100% | 1.0000 | 1.0000 | 1.0000 |
| learned_metric_v0.2.0 | 256 | 0.5609 | 100% | 1.0000 | 1.0000 | 1.0000 |

---

## 5. Interpretation

**Hand-crafted LBP+Gabor features remain the strongest method** on LeaData
public leather texture data. The learned model retrieves same-label nearest
neighbors perfectly (100% NN agreement, R@1 = 1.0) but produces less compact
clusters (separation 0.5609 vs 0.9418).

Several factors likely explain the gap:

1. **Label strategy may be too granular.** `external_item_id` maps to 16
   species/sample groups. Some groups have many images while others have few,
   creating class imbalance. The contrastive pair sampler may not generate
   enough hard negative pairs to push clusters apart effectively.

2. **Generic contrastive loss is a weak objective.** Pairwise contrastive loss
   with random pair sampling does not mine hard negatives or leverage batch
   structure. Supervised contrastive loss or triplet loss with semi-hard mining
   would likely improve separation.

3. **ResNet18 ImageNet features may not transfer well to leather micro-texture.**
   ImageNet pretraining optimizes for object/scene recognition at natural image
   scales. Leather texture at macro/micro scale may not align with these learned
   features. The hand-crafted LBP and Gabor features are specifically designed
   for local texture patterns.

4. **The projection head is small.** A 512→256→256 projection may not provide
   enough capacity to transform ImageNet features into a texture-discriminative
   embedding space. Deeper or wider projection heads may help.

5. **Augmentations may need tuning.** Random resized crop and color jitter are
   generic. Texture-specific augmentations (simulated focus variation, lighting
   angle changes) may be more appropriate for microscopy-adjacent data.

Despite the lower cluster separation, the learned model achieves perfect
retrieval metrics (NN agreement and recall@K), indicating that the embedding
space is functional — just less compact than the hand-crafted baseline.

---

## 6. Recommended Next Experiments

1. **Try species-level label strategy.** If LeaData metadata provides species
   labels distinct from sample groups, these may provide more balanced and
   semantically meaningful classes for contrastive training.

2. **Freeze backbone, train projection head only.** If ImageNet features are
   useful but fine-tuning is over-adapting, freezing the backbone and training
   only the projection head may produce a cleaner embedding space with less
   risk of overfitting on 897 training images.

3. **Switch to supervised contrastive loss.** SupCon uses all positives vs all
   negatives within a batch, providing a richer training signal than pairwise
   contrastive loss. It typically produces better-separated clusters on small
   datasets.

4. **Add hard-negative mining.** Semi-hard negative mining selects the closest
   wrong-class example for each anchor, forcing the model to learn finer
   distinctions. This is especially important when random pair sampling produces
   too many easy negatives.

5. **Try stronger augmentations.** Add Gaussian blur, sharpen, and simulated
   exposure variation. These are more relevant for texture data than the current
   generic augmentations.

6. **Evaluate ResNet50 or ConvNeXt-Tiny** only after the above changes have
   been tested. A larger backbone is unlikely to help if the loss function and
   training strategy are the bottleneck.

7. **Run on FabricNET for comparison** once a label strategy is found that
   supports supervised training (FabricNET currently has 1 image per class,
   limiting contrastive approaches).

---

## 7. Limitations

- LeaData is a public leather texture dataset, not a luxury authentication
  dataset. Results do not measure authentic-vs-counterfeit discrimination.
- The 16-class label structure comes from external dataset metadata, not luxury
  provenance labels.
- The learned model is an experiment artifact, not a production model. It is not
  registered in the backend model registry.
- Training on 897 images with 16 classes is a small-scale experiment. Results
  may not generalize to larger or more diverse datasets.
- No microscope/gold-set data was used. Real luxury texture at microscope
  magnification may behave differently from LeaData macro leather images.
- Generated model artifacts and experiment outputs remain in gitignored
  directories and are not committed.

---

## 8. Related Documents

- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Preprocessing Comparison Results](preprocessing-comparison-results.md)
- [Region-Specific Analysis Results](region-specific-analysis-results.md)
- [OOD Experiment Results](ood-experiment-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
