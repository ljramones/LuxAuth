# ML Improvement Roadmap

**Date:** 2026-04-25
**Status:** Planning — no production authentication claims

This document converts an external technical critique of the LuxAuth MVP into a
prioritized roadmap for ML and image-processing improvements.

---

## 1. Summary of Critique

The external review found:

- **Architecture is strong for an MVP.** The event-driven pipeline, dataset governance,
  evaluation harness, idempotency, and audit trail are well beyond typical prototype
  quality. The separation of raw evidence from normalized derivatives is sound.

- **Biggest weakness is learned metric model maturity.** The learned_metric_v0.1.0 model
  is a lifecycle prototype only — randomly initialized ResNet18 trained for 10 epochs on
  18 synthetic images. It underperforms the hand-crafted baseline, which is expected but
  means the learned-model path has not yet demonstrated value.

- **Quality and normalization need microscopy-specific upgrades.** The current quality
  checks (Laplacian variance, mean luminance, glare ratio) are general-purpose. Real
  microscope images will require tile-based focus uniformity, specular reflection
  detection, and calibration-aware normalization.

- **Real gold-set data is the next major unlock.** No amount of synthetic or public
  external dataset work substitutes for real labeled microscope captures of known-authentic
  and known-counterfeit items with verified provenance.

---

## 2. Accepted Recommendations

These are improvements we intend to implement, roughly in the order listed.

### Image Quality / Normalization
- **Tile-based focus uniformity** — divide the image into a grid and check that sharpness
  is consistent across tiles, not just globally. Microscope images can have sharp centers
  with soft edges.
- **Better glare/specular detection** — the current bright+low-saturation ratio is a
  first pass. Real microscope images of metal hardware and coated leather need
  more targeted specular detection (e.g., highlight connectivity analysis).
- **Color/scale calibration support** — store calibration reference metadata per device
  and apply white-balance or scale corrections during normalization if calibration data
  is available. Do not require calibration for ingestion, but flag its absence.
- **Multi-crop normalization experiment** — compare center-crop (current) against
  multi-crop or padded-resize approaches. Center-crop may discard important edge regions
  on rectangular microscope captures.

### Metric Learning
- **Pretrained backbone** — use ImageNet-pretrained ResNet18 weights as a starting point
  instead of random initialization. This should give the learned model a meaningful
  feature base even with small datasets. Requires internet access for weight download
  (or local weight cache).
- **Better metric-learning losses** — experiment with ArcFace, CosFace, or
  Multi-Similarity Loss as alternatives or supplements to contrastive loss. These
  objectives often produce better-separated embedding spaces on small datasets.
- **Hard/semi-hard negative mining** — the current pair generation is random. Mining
  hard negatives (closest wrong-class examples) forces the model to learn finer
  distinctions. Semi-hard mining is safer for small datasets.
- **Stronger augmentations** — add random erasing, affine transforms, and microscopy-aware
  augmentations (simulated focus variation, lighting angle changes). The current
  augmentations (flip, rotate, color jitter) are mild.
- **Embedding dimension experiment** — compare 128-dim against 256-dim embeddings. Higher
  dimensions may capture more texture detail, but increase storage and search cost.
  Production learned embeddings may need 512-d or 768-d — this decision must be made
  before committing to large-scale real reference embeddings
  (see [ADR-0002](../../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md)).
- **Backbone candidates** — evaluate pretrained ResNet, ConvNeXt, DINOv2-style
  self-supervised models, and ViT/SigLIP-style visual encoders before first serious
  gold-set training. The current randomly-initialized ResNet18 is a lifecycle scaffold only.
- **learned_metric_v1 architecture decision** — make backbone, dimension, and loss
  decisions before real reference library growth. Changing architecture after large-scale
  embedding requires full re-embedding of all references.

### Scoring / Decision
- **Weighted multi-region scoring** — the current decision engine treats all regions
  equally. Some regions (e.g., hardware engraving) may be more discriminative than others.
  Region-specific weights could improve decision quality, but require real data to
  calibrate.

### Baseline Embedding Improvements
- **texture_baseline_v0.2.0 experiment** — ✅ **Implemented.** LBP histogram (64 bins) +
  Gabor filter responses (8 orientations × 4 frequencies) added to the v0.1.0 feature
  set, producing 256-dim embeddings. Cluster separation improved 28–40% on FabricNET and
  LeaData V1 with 100% NN agreement. See
  [results](../datasets/baseline-feature-comparison-results.md). v0.2.0 is a candidate
  enhanced baseline for future learned-model comparison.
- **Preprocessing comparison experiment** — ✅ **Implemented and run.** Six strategies
  compared on FabricNET (full) and LeaData (medium 200-image subset). CLAHE produced
  the best cluster separation on both datasets (+4.9% FabricNET, +2.9% LeaData).
  Center-crop remains the backend default — CLAHE and padded-resize are candidates
  for microscope acceptance testing. See
  [Preprocessing Comparison Results](../datasets/preprocessing-comparison-results.md).
  Patch/tiling strategy remains experimental pending results on real microscope captures.

### OOD Detection
- **Improved out-of-distribution scoring** — the current OOD score is `1 - max_similarity`,
  which is a simple but limited heuristic. Future work should evaluate Mahalanobis distance
  to class centroids, kNN density estimation, Isolation Forest, or Local Outlier Factor.
  These require enough reference data to establish meaningful density estimates and are
  therefore deferred until real gold-set data exists.

### Item Condition and Repair Metadata
- **Condition and repair tracking** — real luxury items may have known repairs, replaced
  components, third-party restoration, or wear-related alterations. The system should
  support per-item and per-region condition metadata:
  - known_repairs flag
  - replaced_components list
  - third_party_repair flag
  - restoration_notes
  - region-level condition flags (original / repaired / replaced / unknown)
- **Routing repaired regions** — regions flagged as repaired or altered should be routed
  to expert review rather than evaluated against standard counterfeit-detection logic.
  A replaced zipper pull is not evidence of counterfeit manufacturing.
- See [Item Condition Vocabulary](../reference/item-condition-vocabulary.md) for the
  canonical values for condition_grade, component_status, component_type, and related fields.

### Data Governance
- **Explicit intra-item leakage rule** — all images from the same physical item must
  remain in the same split. Split assignment must be by `reference_item_id` or
  `external_item_id`, never by individual image. This is partially implemented (current
  promotion scripts split by item) but should be enforced as a hard validation rule in
  the leakage-check step.
- **Small real gold-set protocol** — define a minimum viable capture plan for
  known-authentic and known-counterfeit items. Even 5 authentic + 5 counterfeit items
  with 5 regions each (50 captures per class) would provide a meaningful first real
  evaluation. See [Inspection Region Taxonomy](../reference/luxury-item-inspection-region-taxonomy.md)
  for Tier 1/2 region priorities and coverage gaps.

### Product Latency
- **Result delivery optimization** — the current queue-driven pipeline is correct for
  auditability, idempotency, and local MVP development. A future mobile product may need
  optimized result orchestration: polling endpoints, webhook callbacks, or a synchronous
  fast-path for low-latency decisioning. This is a product/UX concern, not an ML concern,
  and should not change the pipeline architecture prematurely.

---

## 3. Deferred Recommendations

These are valid improvements but are deferred because they depend on production
infrastructure, real traffic, or scale that does not yet exist.

| Recommendation | Why Deferred |
|---|---|
| Production vector DB migration (Milvus, Weaviate) | pgvector is sufficient for local dev and early production on RDS. Migration justified only at scale. |
| Grad-CAM / explainability overlays | Valuable for expert review UI but requires a frontend and real authentication use cases first. |
| Streamlit / web dashboard | Useful for diagnostics but the current CLI + generated reports workflow is adequate for development. |
| Production model drift monitoring | No production traffic exists to drift against. |
| Isotonic regression / Platt scaling for threshold calibration | Requires a large enough validation set with real labels. Current sweep-based calibration is appropriate for the dataset sizes available. |
| SageMaker / Triton production inference | Deferred per ADR-0001 until model lifecycle and throughput warrant managed infrastructure. |
| Adversarial robustness threat model | No production traffic or adversarial threat surface yet. Important before any public-facing deployment. |
| Model drift monitoring | Requires production traffic and baseline performance metrics to detect drift against. |
| Per-brand/material/region threshold calibration | Requires enough labeled real data per category. Current global thresholds are development defaults. |
| Patch-based region embedding | Design needed before implementation; see [architecture note](../../auth-platform/docs/architecture/patch-based-region-embedding.md). |
| Explicit OOD detector (Mahalanobis, kNN density) | ✅ **Experiment framework implemented.** Six OOD scoring methods compared on FabricNET/LeaData cross-domain pairs. Current production query-image UI still uses simple similarity-based interpretation bands. Dedicated OOD scoring remains experimental until validated on real microscope/gold-set data. |

---

## 4. Recommended Execution Order

### Phase 1 — Capture Quality and Microscopy Readiness

**Goal:** Prepare the quality and normalization pipeline for real microscope images.

- Add tile-based sharpness uniformity check (e.g., 4×4 grid, flag if any tile < threshold)
- Add specular highlight connectivity check (clusters of saturated pixels, not just ratio)
- Add capture repeatability diagnostic (same object, same position, 5 captures — measure
  embedding pairwise similarity)
- Store calibration metadata (white balance reference, scale reference) in device
  calibration profiles; flag images captured without calibration
- Document thresholds as development defaults, not validated production values

### Phase 2 — Public External Dataset Diagnostics

**Goal:** Extract maximum diagnostic value from FabricNET and LeaData before real data.

- Run FabricNET and LeaData with texture_baseline_v0.1.0 (done)
- Compare center-crop vs. multi-crop normalization on both datasets (✅ implemented as preprocessing comparison experiment)
- Compare 128-dim vs. 256-dim baseline embeddings
- Generate per-class (species / fabric type) cluster separation reports
- Document which texture features are most discriminative for each dataset
- Parse FabricNET XLSX metadata for richer labels (requires intentionally adding
  openpyxl as an explicit dependency; only worth doing if the metadata meaningfully
  enriches ingestion labels)
- Experiment with texture_baseline_v0.2.0 (add LBP features, optionally Gabor filters)
  and compare against v0.1.0 on both datasets
- Compare center-crop vs. padded-resize vs. multi-crop embedding fusion — document
  which strategy is most consistent for microscope-framed images

### Phase 3 — Gold-Set Capture Protocol

**Goal:** Define what the first real microscope capture session must produce.

- Minimum 5 known-authentic + 5 known-counterfeit items (ideally more)
- All 5 required regions per item
- Multiple images per region (≥3 per protocol)
- Provenance notes: how was authenticity determined?
- Split by physical item — enforce that all images from the same reference_item_id
  remain in the same split (hard validation rule, not just convention)
- SHA-256 and perceptual-hash leakage checks
- Calibration reference captured at session start
- Document capture conditions: device, magnification, lighting, operator
- Record item condition metadata: known repairs, replaced components, restoration notes
- Flag repaired/altered regions for expert review routing
- Include hard cases in the gold set if available:
  - pristine authentic
  - heavily used authentic
  - repaired authentic (disclosed)
  - known counterfeit
  - suspected altered/Franken-bag items (if legally and ethically available)

### Phase 4 — learned_metric_v0.2.0 Experiments

**Goal:** First meaningful learned model comparison against baseline.

**Status:** ✅ First full run completed on LeaData V1. `learned_metric_v0.2.0`
(pretrained ResNet18, contrastive loss, 256-dim, 20 epochs) achieved 100% NN
agreement and R@1 but cluster separation (0.5609) was lower than
texture_baseline_v0.2.0 (0.9418). Hand-crafted LBP+Gabor features remain
strongest on public texture data. Next steps: supervised contrastive loss,
frozen backbone, hard-negative mining. See
[results](../datasets/learned-metric-v02-results.md).

- **Decide backbone and embedding dimension before training** — see [ADR-0002](../../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md)
- ✅ Enable pretrained backbone (ImageNet ResNet18 default)
- ✅ Add stronger augmentations (random resized crop, color jitter, random erasing, rotation)
- Evaluate 128-d vs 256-d vs 512-d embedding dimension (256-d is default)
- Train on gold-set train split — **if the first gold set is too small for meaningful
  training, use it as an evaluation-only benchmark first and defer learned model training
  until sufficient real data exists**
- Evaluate on gold-set test split (never seen during training)
- Compare against texture_baseline_v0.1.0 on the same test split
- Record all training configs, metrics, and artifacts
- Document results conservatively

### Phase 5 — Advanced Metric Learning

**Goal:** Improve embedding quality if Phase 4 shows promise.

- Experiment with ArcFace, CosFace, or Multi-Similarity Loss
- Implement hard-negative or semi-hard negative mining
- Explore region-specific models (one model per capture region)
- Explore multi-task learning (authentication + material classification)
- Calibrate thresholds on validation split after model improvements
- Re-evaluate with updated threshold profiles
- Evaluate improved OOD detection methods (Mahalanobis distance, kNN density, Isolation
  Forest) once reference data is large enough for meaningful density estimates
- Assess product-latency requirements if mobile capture client is active; consider
  polling/webhook/fast-path orchestration without changing the underlying pipeline

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| Public datasets are not luxury-authentication datasets | Use them for pipeline validation only; never claim authentication accuracy from them |
| Gold set may be too small for generalization | Start with narrow scope (one brand, one material); document sample size limitations |
| Capture device artifacts can dominate embeddings | Calibrate devices; include device metadata in analysis; train with device-diverse data if possible |
| Overfitting to synthetic/public data | Evaluate on held-out real data only; never tune on test splits |
| Threshold tuning without real validation can mislead | Label thresholds as development defaults; require real validation before production use |
| Pretrained backbone may not help on microscopy | ImageNet features may not transfer well to microscopic textures; measure empirically |
| Verified counterfeit provenance may be difficult to establish | Record how counterfeit status was determined; use SUSPECT_COUNTERFEIT label or exclude uncertain examples from training/evaluation |
| Repaired or altered items may confuse authentication logic | Track condition/repair metadata per item and region; route altered regions to expert review |
| Intra-item image leakage across splits | Enforce split-by-item as a hard validation rule, not just convention; fail promotion if violated |
| Center-crop discards important edge texture from microscope images | Evaluate multi-crop and padded-resize alternatives before committing to a normalization strategy for real data |
| **Verified data is the strategic bottleneck** | Architecture is no longer the blocker; sourcing authenticated items and verified counterfeits with documented provenance is. See [Dataset Acquisition Strategy](../roadmaps/dataset-acquisition-strategy.md) |

---

## 6. Non-Goals

- **No production authentication claims** from any phase in this roadmap
- **No cloud ML deployment** until model lifecycle and throughput warrant it
- **No commercial guarantee** of authentication accuracy
- **No brand endorsement implication** — LuxAuth is an independent third-party system
- **No real-time mobile inference** until a production model is validated

---

## 7. Acceptance Criteria for Next ML Milestone

The next ML milestone (completion of Phase 3 or Phase 4) is reached when:

- [ ] Real microscope acceptance data has been ingested via the capture batch workflow
- [ ] Image quality metrics have been reviewed on real microscope images and thresholds
      adjusted if needed
- [ ] External dataset diagnostic reports have been generated for FabricNET and LeaData
- [ ] A learned model (v0.2.0 or later) has either been trained on sufficient real data
      and compared against texture_baseline_v0.1.0, or has been explicitly deferred with
      documentation explaining that the first gold set is evaluation-only
- [ ] No train/test data leakage exists (verified by SHA-256 and item-level split checks)
- [ ] All results are documented conservatively — no overclaiming, no production readiness
      assertions without sufficient evidence
- [ ] Evaluation metrics, diagnostic reports, and model artifacts are recorded with full
      versioning and provenance

---

## Related Documents

- [Development Roadmap](../roadmap.md)
- [ML Technology Explained](../ml-technology-explained.md)
- [External Dataset First Run Results](../datasets/external-dataset-first-run-results.md)
- [Public Dataset Evaluation Plan](../datasets/public-dataset-evaluation-plan.md)
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md)
- [ADR-0001: Defer SageMaker](../../auth-platform/docs/architecture/adr-0001-defer-sagemaker.md)
