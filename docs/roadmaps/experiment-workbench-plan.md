# Experiment Workbench Plan

Plan for structured ML experimentation in the LuxAuth project.

## 1. Purpose

Notebooks and experiment configs serve as the exploration and comparison layer for LuxAuth ML research.

- **Notebooks** are for exploration, comparison, and visualization. They are disposable scratch space for trying ideas, comparing approaches, and generating figures.
- **Reusable code** belongs in `auth-platform/ml/`. If a notebook produces a useful function, move it into the package.
- **Notebooks are not production code.** They should never be imported by the platform, called from CI, or treated as a source of truth.
- **Experiment configs** in `experiments/configs/` define reproducible experiment parameters. They are committed to version control.
- **Experiment outputs** in `experiments/outputs/` are gitignored regenerable artifacts. Only curated summaries are promoted to `docs/datasets/results/`.

## 2. Experiment Categories

1. **Preprocessing comparison** -- center-crop vs padded-resize vs multi-crop vs patch/tiling strategies
2. **Hand-crafted feature expansion** -- adding LBP, Gabor, GLCM to the existing texture_baseline histogram features
3. **Backbone comparison** -- ResNet18/50, EfficientNet, ConvNeXt-Tiny, ViT-Tiny, DINOv2, SigLIP/CLIP
4. **Loss function comparison** -- contrastive, triplet, ArcFace, supervised contrastive, and others
5. **Embedding dimension study** -- 64 vs 128 vs 256 vs 512 dimensions across backbones
6. **Region-specific analysis** -- per-region embedding behavior, scoring, and threshold tuning
7. **OOD / novelty detection** -- methods for detecting out-of-distribution inputs
8. **End-to-end pipeline evaluation** -- full capture-to-decision latency and accuracy on held-out test sets

## 3. Candidate Preprocessing Methods

| Method | Description |
|---|---|
| Center crop | Crop to square from center, resize to input_size. Current default. |
| Padded resize | Resize longest edge to target, pad shorter edge. Preserves aspect ratio. |
| Multi-crop | Multiple crops per image (center + corners), embed each, aggregate. |
| Patch / tiling | Divide image into overlapping tiles, embed each, aggregate. |
| Color normalization | White-balance correction to reduce lighting variation. |
| Grayscale conversion | Remove color, focus on texture and structure. |
| CLAHE | Contrast-limited adaptive histogram equalization for local contrast. |
| Glare / specular masking | Detect and mask specular highlights before embedding. |

## 4. Candidate Feature Extractors

| Extractor | Description |
|---|---|
| texture_baseline_v0.1.0 | Current hand-crafted features: grayscale histogram, color histogram, gradient histogram, local variance. 128-dim. |
| LBP (Local Binary Patterns) | Rotation-invariant texture descriptor. Captures micro-texture. |
| Gabor filters | Multi-scale, multi-orientation frequency analysis. Captures texture at different scales. |
| GLCM (Gray-Level Co-occurrence Matrix) | Statistical texture features: contrast, correlation, energy, homogeneity. |
| Hybrid | Concatenation of histogram + LBP + Gabor + GLCM features. |

## 5. Candidate Backbones

| Backbone | Parameters | Pretrained | Notes |
|---|---|---|---|
| ResNet18 | 11M | ImageNet or random | Lightweight baseline. Fast training. |
| ResNet50 | 25M | ImageNet | Standard metric learning backbone. |
| EfficientNet-B0 | 5M | ImageNet | Efficient architecture, good accuracy/compute ratio. |
| ConvNeXt-Tiny | 28M | ImageNet | Modern CNN, strong transfer learning. |
| ViT-Tiny | 6M | ImageNet | Lightweight transformer. May need more data. |
| DINOv2 (ViT-S/14) | 22M | Self-supervised | Strong visual features without labels. Frozen or fine-tuned. |
| SigLIP / CLIP | varies | Vision-language | Zero-shot or fine-tuned. Useful for semantic similarity. |

## 6. Candidate Losses

| Loss | Type | Notes |
|---|---|---|
| Contrastive | Pairwise | Classic. Requires positive/negative pairs. Margin hyperparameter. |
| Triplet | Triplet | Anchor-positive-negative. Semi-hard mining important. |
| Semi-hard triplet | Triplet | Triplet with semi-hard negative mining strategy. |
| Supervised contrastive (SupCon) | Batch | All positives vs all negatives in batch. Temperature hyperparameter. |
| ArcFace | Angular margin | Additive angular margin on cosine similarity. Strong on small datasets. |
| CosFace | Angular margin | Additive cosine margin. Similar to ArcFace. |
| Multi-Similarity | Batch | Mines hard pairs using multiple similarity measures. |
| ProxyAnchor | Proxy-based | One proxy per class. Efficient for large class counts. |

## 7. Candidate Similarity / OOD Methods

| Method | Type | Notes |
|---|---|---|
| Cosine similarity | Distance | Default for normalized embeddings. |
| Euclidean distance | Distance | Standard L2 distance. |
| Mahalanobis distance | Distance | Accounts for feature correlations. Requires covariance estimation. |
| kNN density | Density | Distance to k-th nearest neighbor as OOD score. |
| Isolation Forest | Anomaly | Tree-based anomaly detection. No assumption on distribution. |
| Local Outlier Factor (LOF) | Density | Compares local density to neighbors. Good for clustered data. |
| One-class SVM | Boundary | Learns decision boundary around known classes. |

## 8. Standard Metrics

### Embedding quality
- **NN agreement** -- fraction of queries whose nearest neighbor is same-item
- **Recall@K** -- fraction of queries with a same-item match in top K
- **Cluster separation** -- ratio of inter-class to intra-class distances (silhouette, Davies-Bouldin, or similar)

### Authentication accuracy
- **FPR (false positive rate)** -- fraction of different-item pairs incorrectly matched
- **FNR (false negative rate)** -- fraction of same-item pairs incorrectly rejected
- **Inconclusive rate** -- fraction of queries that fall in the uncertain zone
- **OOD rate** -- fraction of inputs detected as out-of-distribution

### Robustness
- **Per-region metrics** -- all above metrics broken down by inspection region
- **Per-condition metrics** -- metrics broken down by lighting, angle, wear level

### Efficiency
- **Latency** -- wall-clock time per embedding (CPU and GPU)
- **Norm statistics** -- mean and standard deviation of embedding L2 norms (stability indicator)

## 9. Experiment Record Format

Every experiment must be recorded with the following YAML structure:

```yaml
experiment_id: <unique identifier>
dataset_version: <governed dataset version tag>
model_version: <model or feature extractor version>
preprocessing_version: <preprocessing pipeline version>
backbone: <backbone name or "none">
loss: <loss function name or "none">
embedding_dimension: <integer>
augmentation_config: <description or path to augmentation config>
region_scope: <"all" or list of regions>
train_split: <split name>
validation_split: <split name>
test_split: <split name>
metrics:
  nn_agreement: <float>
  cluster_separation: <float>
  recall_at_5: <float>
  fpr: <float>
  fnr: <float>
  inconclusive_rate: <float>
  ood_rate: <float>
  latency_ms: <float>
notes: <free-form observations>
```

## 10. Notebook Rules

1. **Start from governed dataset versions.** Never load raw images directly -- use the dataset loader with a version tag.
2. **Never split by image when physical item IDs exist.** Splits must be by item to avoid data leakage.
3. **Never mix synthetic/public/lab data without explicit purpose.** Each data source must be clearly labeled and justified.
4. **Never treat public datasets as authentication proof.** Public data is for development and relative comparison only.
5. **Record config and random seed.** Every notebook must load its config from `experiments/configs/` or define it in the first cell.
6. **Save outputs under `experiments/outputs/`.** Never save outputs in the notebook directory.
7. **Curated summaries go to `docs/datasets/results/`.** Only promote results that are worth preserving long-term.
8. **Do not import notebooks.** If code is reusable, move it to `auth-platform/ml/`.
9. **Keep notebooks self-contained.** Each notebook should run top-to-bottom without external state.
10. **Clear outputs before committing.** Notebook outputs are regenerable and should not be in version control.

## 11. Initial Notebook Contents

Each notebook follows a standard structure:

1. **Imports** -- standard library, project imports, config loading
2. **Config** -- load experiment config from YAML or define inline
3. **Dataset loading** -- load governed dataset version, print summary
4. **Sanity checks** -- verify splits, label counts, image dimensions, no leakage
5. **Experiment placeholder** -- the main experiment code (model training, feature extraction, comparison, etc.)
6. **Metrics** -- compute standard metrics from section 8
7. **Visualization** -- plots, confusion matrices, embedding projections (t-SNE/UMAP)
8. **Notes** -- markdown cell for observations and next steps

### Per-notebook specifics

- **00-dataset-inspection**: Load dataset, print split sizes, label distribution, sample images per region, check for duplicates.
- **01-preprocessing-comparison**: Apply each preprocessing method, visually compare outputs, measure information loss.
- **02-baseline-embedding-comparison**: Run texture_baseline variants, compute pairwise distances, compare cluster quality.
- **03-metric-learning-experiments**: Train a single backbone+loss config, evaluate on validation set, save embeddings.
- **04-loss-function-comparison**: Fix backbone, vary loss function, compare embedding quality metrics.
- **05-backbone-comparison**: Fix loss, vary backbone, compare accuracy and latency.
- **06-region-specific-analysis**: Run best model per-region, analyze which regions are hardest, suggest region-specific thresholds.
- **99-experiment-summary-template**: Markdown-heavy template with sections for hypothesis, setup, results, conclusions, next steps.

## First Implemented Experiment

**texture_baseline_v0.1.0 vs texture_baseline_v0.2.0** on FabricNET and LeaData V1.

v0.2.0 adds LBP histogram (64 bins) and Gabor filter responses (64 values) to the
v0.1.0 feature set, producing 256-dim embeddings. Cluster separation improved 28–40%
while NN agreement remained 100%.

These are public external datasets — results validate texture feature behavior, not
authentication accuracy. See [Baseline Feature Comparison Results](../datasets/baseline-feature-comparison-results.md).

## Second Implemented Experiment

**Preprocessing comparison** on FabricNET and LeaData V1 using texture_baseline_v0.2.0.

Six strategies compared:
- `center_crop_512` — current backend default (baseline)
- `padded_resize_512` — preserves full field of view with reflect padding
- `five_crop_512` — center + 4 corner crops, embeddings averaged + L2-normalized
- `grayscale_center_crop_512` — tests color dependence
- `clahe_center_crop_512` — CLAHE on luminance channel for local contrast enhancement
- `tile_224_average` — non-overlapping 224x224 tiles, embeddings averaged + L2-normalized

CLAHE consistently produced the best cluster separation across both datasets
(+4.9% on FabricNET, +2.9% on LeaData medium). Center-crop remains the backend
default until evidence from real microscopy data supports changing it. These
results are diagnostic only — they do not prove authentication accuracy. See
[Preprocessing Comparison Results](../datasets/preprocessing-comparison-results.md).

**Runtime note:** Full LeaData preprocessing across all 6 strategies can be slow
(1,200 images × multi-crop/tile strategies). Use quick/medium Makefile targets
for iteration:
- `make preprocessing-experiment-leadata-quick` — 50 images, 3 fast strategies
- `make preprocessing-experiment-leadata-medium` — 200 images, 3 fast strategies
- `make preprocessing-experiment-leadata` — full run (overnight if needed)

## Third Implemented Experiment

**Region-specific analysis scaffold** for coverage, readiness, and per-region
embedding diagnostics.

- Computes per-region image/item counts, split distribution, label distribution,
  embedding coverage, and readiness levels (no_data / sparse / diagnostic_only /
  evaluation_ready / training_candidate).
- Computes per-region embedding metrics (cluster separation, NN agreement, recall@K)
  where sufficient data exists.
- Includes minimal region taxonomy registry based on the
  [Inspection Region Taxonomy](../reference/luxury-item-inspection-region-taxonomy.md).
- Flags external-only regions, unknown region codes, and sparse coverage.

This phase is mostly structural — true region-specific conclusions require real
microscope/gold-set capture data with multiple regions per item. Current public
external datasets use single EXTERNAL_* region codes, limiting per-region
comparison within those datasets. See
[Region-Specific Analysis Results](../datasets/region-specific-analysis-results.md).

## Fourth Implemented Experiment

**OOD / out-of-distribution scoring experiment** using FabricNET and LeaData as
cross-domain ID/OOD pairs.

Six scoring methods compared:
- `max_similarity` — current simple proxy (1 - max cosine similarity)
- `mean_topk` — average top-K similarities, more robust to single-neighbor noise
- `similarity_gap` — top-1 minus top-2, measures ambiguity
- `knn_density` — mean similarity to k nearest neighbors as density proxy
- `mahalanobis` — statistical distance to reference distribution
- `lof` — local outlier factor approximation using kNN density ratios

This experiment comes before learned neural models because understanding OOD
behavior with hand-crafted features establishes a diagnostic baseline. The
current query-image UI uses simple similarity-based interpretation bands;
dedicated OOD scoring is experimental and not promoted to the UI until validated
on real data.

## 12. Related Documents

- [ML Improvement Roadmap](ml-improvement-roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [Dataset Acquisition Strategy](dataset-acquisition-strategy.md)
- [Baseline Feature Comparison Results](../datasets/baseline-feature-comparison-results.md)
- [Preprocessing Comparison Results](../datasets/preprocessing-comparison-results.md)
- [Region-Specific Analysis Results](../datasets/region-specific-analysis-results.md)
