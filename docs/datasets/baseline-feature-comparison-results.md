# Baseline Feature Comparison Results

**Date:** 2026-04-26
**Status:** Curated summary — texture feature diagnostics on public external datasets

## 1. Executive Summary

`texture_baseline_v0.2.0` improves cluster separation over `v0.1.0` by 28–40% on both
FabricNET and LeaData V1 while maintaining 100% nearest-neighbor agreement. The enhanced
features (LBP histogram + Gabor filter responses) capture additional texture structure
that the original histogram/gradient/local-variance baseline does not.

**These results validate public texture/material embedding behavior only. They do not
prove luxury authentication accuracy.** Real microscope and gold-set data are required
for authentication-relevant conclusions.

## 2. Experiment Setup

| Parameter | Value |
|---|---|
| Datasets | external_fabricnet_v0.1.0 (130 images), external_leadata_v0.1.0 (1,200 images) |
| Extractors | texture_baseline_v0.1.0 (128-dim), texture_baseline_v0.2.0 (256-dim) |
| Split | all (no train/test distinction — diagnostic comparison) |
| Preprocessing | normalize_image_v0.1.0 (EXIF fix, RGB, center-crop, 512×512 PNG) |
| Metrics | Cluster separation, NN agreement, recall@K, pairwise similarity, embedding norms |
| Runner | `scripts/run_baseline_feature_experiment.py` |
| Outputs | `experiments/outputs/baseline-feature-comparison/` (gitignored) |

### Feature Composition

| Extractor | Features | Bins/Values | Total Dim |
|---|---|---|---|
| v0.1.0 | Grayscale histogram + color histograms + gradient histogram + local variance | 32 + 48 + 32 + 16 | 128 |
| v0.2.0 | v0.1.0 features + LBP histogram + Gabor filter responses | 128 + 64 + 64 | 256 |

v0.2.0 LBP: 8-neighbor local binary pattern with 64-bin histogram.
v0.2.0 Gabor: 8 orientations × 4 frequencies (λ=4,8,16,32) × mean+std of filtered response.

Both extractors L2-normalize the final vector to unit length.

## 3. Results

| Dataset | Extractor | Dim | Norm Mean | Cluster Sep | NN Agreement | Recall@1 | Recall@3 | Recall@5 | Same-Label Sim |
|---|---|---|---|---|---|---|---|---|---|
| FabricNET | v0.1.0 | 128 | 1.0000 | 0.7227 | 100.0% | 100.0% | 100.0% | 100.0% | 0.7227 |
| FabricNET | **v0.2.0** | 256 | 1.0000 | **0.9242** | 100.0% | 100.0% | 100.0% | 100.0% | 0.9242 |
| LeaData | v0.1.0 | 128 | 1.0000 | 0.6730 | 100.0% | 100.0% | 100.0% | 100.0% | 0.6730 |
| LeaData | **v0.2.0** | 256 | 1.0000 | **0.9418** | 100.0% | 100.0% | 100.0% | 100.0% | 0.9418 |

Diff-label similarity is 0.0 for both datasets because FabricNET and LeaData are
single-class (`PUBLIC_DATASET_CLASS`) external datasets. The cluster separation score
reflects intra-dataset texture variation rather than authentic-vs-counterfeit discrimination.

## 4. Interpretation

- **LBP and Gabor features improve texture-class separation.** The LBP histogram captures
  local spatial structure (edge patterns, corners, flat regions) that global histograms
  miss. Gabor responses capture oriented frequency content at multiple scales.

- **The improvement is consistent across both datasets** — 28% on FabricNET (woven fabric)
  and 40% on LeaData (leather grain). This suggests the additional features capture
  meaningful texture structure rather than dataset-specific artifacts.

- **NN agreement remains perfect** at 100% for both extractors on both datasets. This is
  expected because the datasets have broad single-class labels where all images are
  "similar" — the extractors distinguish texture variation within the class, not between
  opposing classes.

- **v0.2.0 is a candidate enhanced baseline** for future comparison against learned metric
  models. It establishes a higher floor before neural approaches are introduced.

## 5. Limitations

- **FabricNET and LeaData are not authentic-vs-counterfeit luxury datasets.** They contain
  public microscopic textures used for pipeline validation. Cluster separation on these
  datasets does not predict authentication performance.

- **NN agreement is high partly because labels are broad.** A single-class dataset where
  all images share the same label produces trivially high NN agreement. Meaningful NN
  disagreement requires multi-class data with clear label boundaries.

- **Cluster separation does not equal authentication performance.** A high separation
  score means embeddings from the same label are more similar to each other than to
  embeddings from different labels. On single-class data, this measures internal texture
  consistency rather than discrimination.

- **v0.2.0 increases vector dimension from 128 to 256.** This doubles storage and
  slightly increases search cost. The trade-off is acceptable for diagnostics but should
  be evaluated against pgvector index performance at scale.

- **Real microscope/gold-set data is still required** to validate whether LBP and Gabor
  features improve authentication-relevant texture discrimination.

## 6. Recommended Next Steps

1. **Expose v0.2.0 as a selectable experimental extractor** in the embedding service or
   diagnostics pipeline (do not replace v0.1.0 as default yet)
2. **Re-embed external datasets with v0.2.0** to enable side-by-side query-image
   comparison in the workbench
3. **Compare query-image nearest-neighbor behavior** under v0.1.0 vs v0.2.0
4. **Evaluate on first microscope/lab captures** when available — this is the real test
5. **Keep v0.1.0 as the current stable baseline** until v0.2.0 is validated on
   authentication-relevant data
6. **Consider v0.2.0 as the baseline target** for learned_metric_v0.2.0 to beat

## Related Documents

- [Experiment Workbench Plan](../roadmaps/experiment-workbench-plan.md)
- [ML Improvement Roadmap](../roadmaps/ml-improvement-roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [External Dataset First Run Results](external-dataset-first-run-results.md)
- [Public Dataset Evaluation Plan](public-dataset-evaluation-plan.md)
