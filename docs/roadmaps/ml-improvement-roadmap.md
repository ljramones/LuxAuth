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
- **Better metric-learning losses** — ✅ **Medium comparison completed.** Contrastive
  (0.7258) and batch-hard triplet (0.7127) are competitive at 5 epochs / 300
  images; both exceed texture_baseline_v0.1.0 (0.6730) but remain below v0.2.0
  (0.9418). SupCon (0.6483) trails but improved 3× from quick run. Next step is
  label strategy experiments, not more loss functions. See
  [results](../datasets/loss-function-comparison-results.md).
- **Hard/semi-hard negative mining** — ✅ **Batch-hard triplet implemented.** Mining
  hard negatives (closest wrong-class examples) forces the model to learn finer
  distinctions. Semi-hard mining is safer for small datasets.
- **Label strategy comparison** — ✅ **Medium comparison completed.** external_item_id
  (16 classes) consistently outperforms species (4 classes) — contrastive +
  external_item_id: 0.7258 vs species: 0.1501; batch-hard: 0.7127 vs 0.3507.
  Finer labels provide stronger training signal. Use external_item_id as default.
  See [results](../datasets/label-strategy-comparison-results.md).
- **Stronger augmentations** — ✅ **Augmentation profiles implemented.** Four profiles
  (none/light/medium/strong) with random erasing, blur, stronger jitter. Comparison
  framework tests augmentation alongside optimizer (Adam/AdamW), scheduler
  (none/cosine), and projection head (256/512). Microscopy-aware augmentations
  remain future work pending real microscope data.
- **Embedding dimension experiment** — compare 128-dim against 256-dim embeddings. Higher
  dimensions may capture more texture detail, but increase storage and search cost.
  Production learned embeddings may need 512-d or 768-d — this decision must be made
  before committing to large-scale real reference embeddings
  (see [ADR-0002](../../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md)).
- **Backbone candidates** — ✅ **Comparison framework implemented.** ResNet18 vs
  ResNet50, frozen vs fine-tuned, 256d vs 512d compared on LeaData V1. ConvNeXt,
  DINOv2, ViT/SigLIP deferred until ResNet results are analyzed. Pretrained
  backbone is now the default (no more random init).
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

### Phase 6 — Few-Shot Prototype Matching and Foundation-Model Backbone

**Goal:** Make LuxAuth's already-few-shot inference path explicit; calibrate the
support-set size needed for stable scoring; evaluate a frozen DINOv2 backbone
as a production embedding candidate.

- Compare inference strategies (nearest-neighbor, top-k mean, prototype
  centroid, prototype medoid, prototype centroid with abstention) at K = 1, 3,
  5, 10 with 500 episodes per cell, on LeaData with FabricNET as OOD
- Compare embedding regimes (`texture_baseline_v0.2.0`, `learned_metric_v0.2.0`,
  `dinov2_base_frozen_v0.1.0`) on the same harness so the support-set
  stabilization curve is measured against multiple embedding qualities
- Sweep abstention thresholds rather than picking one fixed pair; produce
  accuracy-vs-abstention-rate curves for downstream calibration
- Persist results under `experiments/outputs/few-shot/` with full provenance
- Document explicitly: diagnostic only on public texture data; LeaData species
  is not authentic-vs-counterfeit; required K on luxury data is likely higher
- Deferred parallel track (Phase 6c): PatchCore-style anomaly detection over
  an authentic-only memory bank — see Phase 7 §12 for trigger conditions

**Phase 6 status: complete.** Phase 10 of the experiment workbench (this
roadmap's Phase 6) executed; results showed DINOv2 strongly outperforming
`texture_baseline_v0.2.0` on the LeaData diagnostic harness. See
[Few-Shot Prototype Matching Results](../datasets/few-shot-prototype-results.md).
Promotion of DINOv2 to production decision authority is **not** a Phase 6
output — it is gated on Phase 7 shadow operation (below) and pre-declared
promotion criteria.

### Phase 7 — DINOv2 Shadow Integration

**Goal:** Convert "diagnostic-stronger on public data" into "operationally-stronger
on real captures, with documented evidence and pre-declared promotion criteria"
through a bounded shadow window. The production decision authority remains
`texture_baseline_v0.2.0` for the entire shadow period.

This is a deliberately conservative phase. Running the empirically-weaker
model in production while gathering evidence on the candidate is a chosen
tradeoff, not an oversight.

- **Phase 7A:** DINOv2 model-version registration (already present), candidate
  threshold profile registration (`dinov2_base_frozen_default`, status
  `candidate / diagnostic`), `threshold_profiles` schema extensions for
  `margin_threshold` and `description` columns, `learned_metric_v0.2.0`
  historical-comparison gap closure, embedding-service production deployment
  readiness
- **Phase 7B:** DINOv2 reference-dataset re-embedding across all governed
  reference datasets that will be used in shadow scoring; pgvector / HNSW
  capacity verification at production scale (768-d ≈ 3× texture_baseline);
  Data Explorer / workbench tooling updates
- **Phase 7C:** Capture-workbench query path supports DINOv2 scoring alongside
  `texture_baseline`; side-by-side comparison view for diagnostic use
- **Phase 7D:** Dual-strategy DINOv2 shadow logging in the production scoring
  path. `region-scoring-service` computes and logs nearest_neighbor,
  top_k_mean, prototype_centroid, and prototype_medoid scores **in parallel**
  for every region in every session. Production decision behavior unchanged.
  Per-region K logged. **Start of the 4-week / 100-session shadow window.**
- **Phase 7E:** Real-capture threshold and strategy recalibration after
  shadow data accumulates. Recalibrate thresholds on real distributions;
  compare strategies on real data; compute per-region K stability curves;
  identify abstention curve elbow on real distributions
- **Phase 7F:** Promotion decision review against pre-declared §7 criteria
  in the [DINOv2 Shadow Integration Plan](dinov2-shadow-integration-plan.md).
  Either propose promotion with documented rationale, or extend shadow
  operation, or revise approach. Promotion is a deliberate written event,
  not an automatic flip.

**Critical design constraints carried forward from Phase 6 evidence review:**

- Phase 7 must not lock in nearest_neighbor as the production strategy. NN
  beat prototype_centroid on LeaData; this is hypothesized to be
  LeaData-specific (low intra-class variance) and may flip on real data
  with higher intra-class variance. Strategy selection is a Phase 7F
  decision based on real-capture evidence, not a Phase 7A design choice.
- The (0.80, 0.10) threshold values from Phase 6 are LeaData-derived starting
  points only. Production threshold calibration is a Phase 7E output.
- Phase 6c (PatchCore) is deferred until real hard-OOD probes exist; trigger
  conditions are listed in the [DINOv2 Shadow Integration Plan §12](dinov2-shadow-integration-plan.md#12-patchcore-relationship-phase-10c).
- Deferred until real data exists: episodic ProtoNet training; LoRA
  fine-tuning of DINOv2 on luxury microscopy.

The full shadow integration plan, including pre-declared promotion criteria,
shadow scoring architecture, candidate threshold profile spec, per-region K
calibration strategy, and risk register, lives at
[DINOv2 Shadow Integration Plan](dinov2-shadow-integration-plan.md).

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
- [Few-Shot Prototype Matching Results](../datasets/few-shot-prototype-results.md)
- [Public Dataset Evaluation Plan](../datasets/public-dataset-evaluation-plan.md)
- [Microscope Acceptance Runbook](../operations/microscope-acceptance-runbook.md)
- [ADR-0001: Defer SageMaker](../../auth-platform/docs/architecture/adr-0001-defer-sagemaker.md)
