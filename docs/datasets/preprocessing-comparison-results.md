# Preprocessing Comparison Results

**Date:** 2026-04-27
**Status:** Diagnostic — no production authentication claims

---

## 1. Executive Summary

Phase 2 of the Experiment Workbench compared six preprocessing strategies using
`texture_baseline_v0.2.0` (256-dim LBP+Gabor features) on two public external
texture/material datasets:

- **FabricNET** — full dataset (130 images), all 6 strategies
- **LeaData V1** — bounded medium run (200 of 1,200 images), 3 strategies

CLAHE (contrast-limited adaptive histogram equalization) consistently produced
the highest cluster separation across both datasets (+4.9% over center-crop on
FabricNET, +2.9% on LeaData medium). All strategies achieved 100% NN agreement
and perfect recall@K on these datasets.

These are public texture/material datasets. Results validate preprocessing
behavior on texture data — they do **not** prove luxury authentication accuracy.
The goal is to understand preprocessing effects before real microscope/gold-set
capture.

---

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Datasets | `external_fabricnet_v0.1.0`, `external_leadata_v0.1.0` |
| Feature extractor | `texture_baseline_v0.2.0` (256-dim) |
| FabricNET scope | Full dataset (130 images, all splits) |
| LeaData scope | Bounded medium run (200 images, first 200 by DB order) |

### Strategies tested

| Strategy | FabricNET | LeaData medium | Description |
|---|---|---|---|
| `center_crop_512` | Yes | Yes | Current backend default. Center crop to square, resize 512x512. |
| `padded_resize_512` | Yes | Yes | Fit within 512x512 preserving aspect ratio, reflect-pad remainder. |
| `five_crop_512` | Yes | No | Center + 4 corner crops, embed each, average + L2-normalize. |
| `grayscale_center_crop_512` | Yes | No | Center crop, convert to grayscale (3-ch RGB). Tests color dependence. |
| `clahe_center_crop_512` | Yes | Yes | Center crop + CLAHE on luminance channel. Enhances local contrast. |
| `tile_224_average` | Yes | No | Non-overlapping 224x224 tiles, embed each, average + L2-normalize. |

LeaData medium excluded `five_crop_512`, `grayscale_center_crop_512`, and
`tile_224_average` because multi-crop and tile strategies multiply embedding
work per image, making a full 1,200-image run with all strategies prohibitively
slow for iterative development.

---

## 3. FabricNET Results

Full dataset: 130 images, all 6 strategies, `texture_baseline_v0.2.0`.

| Strategy | Images | Cluster sep | NN agree | R@1 | R@3 | R@5 | Same-label | Diff-label | Runtime |
|---|---|---|---|---|---|---|---|---|---|
| center_crop_512 | 130 | 0.9242 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9242 | 0.0000 | 18.8s |
| padded_resize_512 | 130 | 0.9242 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9242 | 0.0000 | 19.0s |
| five_crop_512 | 130 | 0.9247 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9247 | 0.0000 | 95.5s |
| grayscale_center_crop_512 | 130 | 0.9253 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9253 | 0.0000 | 18.9s |
| clahe_center_crop_512 | 130 | **0.9698** | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9698 | 0.0000 | 19.4s |
| tile_224_average | 130 | 0.9284 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9284 | 0.0000 | 29.1s |

**Best cluster separation:** `clahe_center_crop_512` (0.9698) — 4.9% higher than
center-crop baseline (0.9242).

All strategies achieved 100% NN agreement and perfect recall@K. All embeddings
are unit-normalized (norm mean = 1.0). Different-label mean is 0.0 because
FabricNET external images are labeled with a single `PUBLIC_DATASET_CLASS` value
per fabric type and the texture features produce well-separated clusters.

---

## 4. LeaData Medium Results

Bounded medium run: 200 of 1,200 images, 3 strategies, `texture_baseline_v0.2.0`.

| Strategy | Images | Cluster sep | NN agree | R@1 | R@3 | R@5 | Same-label | Diff-label | Runtime |
|---|---|---|---|---|---|---|---|---|---|
| center_crop_512 | 200 | 0.9428 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9428 | 0.0000 | 30.1s |
| padded_resize_512 | 200 | 0.9446 | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9446 | 0.0000 | 30.6s |
| clahe_center_crop_512 | 200 | **0.9697** | 100.0% | 1.0000 | 1.0000 | 1.0000 | 0.9697 | 0.0000 | 30.8s |

**Best cluster separation:** `clahe_center_crop_512` (0.9697) — 2.9% higher than
center-crop baseline (0.9428).

This is a bounded medium run (200 images of 1,200). Results may differ on the
full dataset. Different-label mean is 0.0 for the same labeling reason as FabricNET.

---

## 5. Cross-Dataset Interpretation

**CLAHE is consistently the top strategy by cluster separation** on both FabricNET
(0.9698) and LeaData medium (0.9697). The improvement over center-crop is modest
but consistent: +4.9% on FabricNET and +2.9% on LeaData.

**Padded resize** shows a marginal improvement over center-crop on LeaData (0.9446
vs 0.9428) and is identical on FabricNET. It preserves the full field of view,
which may matter more for microscope captures where important texture is near edges.

**Center-crop remains acceptable.** It achieves 100% NN agreement and perfect
recall@K on both datasets. The cluster separation difference is small enough that
center-crop is not a liability on these datasets.

**Grayscale** (FabricNET only) produced slightly higher cluster separation than
center-crop (0.9253 vs 0.9242), suggesting that color contributes little to the
texture_baseline_v0.2.0 features on this dataset. This makes sense — the v0.2.0
features are dominated by LBP and Gabor, which operate on luminance.

**Five-crop and tile strategies** (FabricNET only) produced slight improvements
in cluster separation (+0.05% and +0.45% respectively) at significant runtime
cost (5x and 1.5x respectively). They are not cost-effective for iteration but
remain interesting as proxies for future patch-based embedding approaches.

**Preprocessing effects appear small on these datasets.** All strategies saturate
NN agreement and recall@K. The discriminating metric is cluster separation, where
differences are modest. Real microscope images — with more variable framing,
lighting, and magnification — may show larger preprocessing effects.

---

## 6. Recommendation

1. **Keep `center_crop_512` as the backend default.** It is adequate on these
   datasets and changing normalization prematurely would complicate pipeline
   reproducibility.

2. **Mark `clahe_center_crop_512` as a candidate for microscope acceptance testing.**
   It consistently produces the best cluster separation, suggesting that local
   contrast enhancement helps the hand-crafted texture features. Real microscope
   images with variable lighting may benefit more.

3. **Mark `padded_resize_512` as a candidate if full-field preservation matters.**
   Microscope captures may have important texture near image edges that center-crop
   discards. This should be tested on real captures.

4. **Keep `five_crop_512` and `tile_224_average` as future experiment candidates.**
   They are proxies for patch-based and multi-view embedding strategies. Their
   runtime cost is justified only when exploring region-specific or patch-level
   embedding architectures.

5. **Do not change backend normalization until real microscope/gold-set data
   confirms these results.** Public texture datasets are not luxury authentication
   datasets.

---

## 7. Runtime Notes

Full LeaData (1,200 images) across all 6 strategies can be slow because
`five_crop_512` (5x embeddings per image) and `tile_224_average` (variable tiles
per image) multiply embedding work. Quick and medium targets exist for iteration:

```bash
# Quick: 50 images, 3 fast strategies (~23s)
make preprocessing-experiment-leadata-quick

# Medium: 200 images, 3 fast strategies (~92s)
make preprocessing-experiment-leadata-medium

# Full: 1,200 images, all 6 strategies (schedule overnight)
make preprocessing-experiment-leadata

# FabricNET full: 130 images, all 6 strategies (~3.5 min)
make preprocessing-experiment-fabricnet
```

---

## 8. Limitations

- FabricNET and LeaData are public material/texture datasets, not luxury
  authentication datasets.
- Cluster separation does not equal authentication accuracy.
- LeaData medium is a 200-image subset of 1,200 — results may differ on the
  full dataset.
- All strategies saturate NN agreement and recall@K on these datasets, so
  cluster separation is the only discriminating metric.
- Different-label mean is 0.0 because external datasets use single-class
  `PUBLIC_DATASET_CLASS` labels — inter-class separation is not measurable.
- Strategy performance may change significantly on real microscope images with
  variable lighting, magnification, and framing.
- No production decision logic should change based on these results alone.

---

## 9. Next Steps

1. Use preprocessing insights during microscope acceptance testing — compare
   CLAHE and padded-resize against center-crop on real microscope captures.
2. Re-run on gold-set data once available with real authentic/counterfeit labels.
3. Only change backend normalization after results on real data confirm the
   benefit.
4. Feed tile/multi-crop results into patch-based region embedding design when
   that experiment track begins.
5. Consider running full LeaData all-strategy experiment overnight for
   completeness.

---

## Related Documents

- [Baseline Feature Comparison Results](baseline-feature-comparison-results.md)
- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
