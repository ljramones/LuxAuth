# LuxAuth ML Technology Explained

## 1. Executive Summary

LuxAuth is an evidence-processing and similarity-scoring platform for AI-assisted luxury
goods authentication. It is **not** a simple "fake/not fake" binary classifier.

The system captures or ingests microscopic images, validates image quality, normalizes
them into standardized derivatives, generates vector embeddings, compares those embeddings
against governed reference datasets using cosine similarity search, scores region-level
evidence, and produces conservative authentication decisions with full evidence lineage.

The current implementation is a **local MVP/prototype** running 13 FastAPI microservices
in Docker Compose with PostgreSQL+pgvector and LocalStack (S3/SQS). It supports:

- Synthetic test data for pipeline validation
- Public external texture/material datasets (LeaData, FabricNET) for embedding behavior evaluation
- Future microscope lab capture datasets for real authentication development
- Future mobile capture clients for field use

**Public datasets and synthetic data validate pipeline behavior, not luxury authentication
accuracy.** Real authentication capability requires verified microscope datasets with
chain-of-custody provenance, which do not yet exist in this system.

---

## 2. Core ML Idea: Material Fingerprinting

The goal of LuxAuth is to compare microscopic or high-quality texture and material
evidence from a questioned item against a reference library of known-authentic and
known-counterfeit samples.

Rather than asking "is this a Chanel bag?", the system asks:

> "How similar are the microscopic manufacturing signatures of this item to known
> authentic and known counterfeit references for this brand, material, region, and
> production era?"

The system examines material and manufacturing features across defined capture regions:

| Region | What the System Examines |
|---|---|
| Leather/canvas grain | Pore structure, fiber pattern, coating texture |
| Stitching detail | Thread twist, stitch spacing, hole morphology |
| Hardware engraving | Edge quality, machining marks, plating texture |
| Printed logos/canvas | Ink edges, raster patterns, print registration |
| Heat stamps/embossing | Impression depth, edge sharpness, pressure marks |

This is fundamentally a **similarity problem**, not just a classification problem.
Authentication requires comparing evidence to a growing, version-controlled reference
library — not predicting a fixed set of class labels.

---

## 3. Why Not a Simple CNN Classifier?

A standard CNN image classifier learns to assign images to a fixed set of classes
("authentic Chanel", "fake Chanel", "authentic LV", etc.). This approach has critical
limitations for authentication:

**New items constantly appear.** Brands release new models, materials, and production
variations every season. A classifier trained on 2024 production may fail on 2025
production unless retrained.

**The reference library grows.** Each newly verified authentic item should strengthen
future comparisons. A classifier does not naturally support incremental reference
addition — it requires full retraining.

**Open-set recognition is required.** The system must handle items it has never seen
before (new models, rare vintage, unfamiliar materials). A classifier produces
meaningless confidence scores on out-of-distribution inputs.

**The answer is distance, not class.** Authentication needs to know *how similar* the
evidence is to known references, with a confidence score — not just which bucket it
falls into.

LuxAuth therefore uses **metric learning and vector search** as the core comparison
mechanism. Classifiers may still be used for auxiliary tasks (region validation,
material prediction, quality gating), but the authentication evidence comparison is
similarity-based.

---

## 4. End-to-End Image Pipeline

```text
Image Source
  │ evidence-asset-service (scan uploads)
  │ capture-intake-service (live capture API)
  │ ingest scripts (batch/external ingestion)
  ▼
Raw Evidence Storage (S3, preserved separately from derivatives)
  │
  ▼
image-quality-service
  │ sharpness, exposure, glare checks
  │ FAIL → image preserved but should not advance through standard pipeline
  │ PASS ↓
  ▼
normalization-service
  │ EXIF fix → RGB → center-crop → 512×512 PNG
  ▼
embedding-service
  │ texture_baseline_v0.1.0 (hand-crafted features)
  │ or learned_metric_v0.1.0 (PyTorch model)
  │ → 128-dim unit-normalized vector
  ▼
vector-search-service
  │ pgvector cosine similarity search
  │ filtered by region, model version, dataset membership
  │ → nearest authentic + counterfeit references
  ▼
region-scoring-service
  │ STRONG_MATCH / MODERATE_MATCH / WEAK_MATCH / MISMATCH / INCONCLUSIVE
  ▼
decision-service
  │ aggregates all required regions
  │ → VERIFIED / UNVERIFIED / INCONCLUSIVE / EXPERT_REVIEW_REQUIRED
```

The pipeline is **event-driven** via SQS queues. Each service publishes to the next
queue. Processing is idempotent (via `processing_runs` table) and carries correlation
IDs through HTTP headers, SQS envelopes, structured logs, and audit events.

The canonical pipeline input is the `image_assets` table — whether an image arrives via
scan upload, live capture session, or batch ingestion, it enters the same quality →
normalization → embedding → search → scoring → decision flow.

---

## 5. Evidence Sources

| Source | Prefix | Purpose | Current Status |
|---|---|---|---|
| Synthetic data | `synthetic_*` | Internal pipeline testing | Implemented |
| Smoke data | `smoke_*` | Disposable workflow validation | Implemented |
| Public external datasets | `external_*` | Texture/material pipeline validation | Implemented (LeaData, FabricNET) |
| Lab/microscope captures | `lab_*` | Real controlled capture datasets | Framework ready, awaiting microscope |
| Production scans | (no prefix) | Future live authentication | Not yet implemented |

These categories **must not be mixed**. Each has its own dataset version prefix,
governance rules, and evaluation context. External public datasets validate pipeline
behavior on real textures but do not prove luxury authentication accuracy. Real lab
captures require stricter metadata, calibration records, and label provenance.

---

## 6. Image Quality Technology

Before any ML processing, images must pass quality validation. Bad evidence produces
unreliable embeddings and misleading similarity scores.

**Current quality checks** (implemented in `auth_common.imaging.compute_quality_metrics`
using OpenCV):

| Check | Method | Threshold | Issue Code |
|---|---|---|---|
| Sharpness | Variance of Laplacian | < 0.15 → fail | `LOW_SHARPNESS` |
| Exposure | Mean luminance | < 40 → underexposed, > 220 → overexposed | `UNDEREXPOSED` / `OVEREXPOSED` |
| Glare | Bright + low-saturation pixel ratio | > 15% → fail | `EXCESSIVE_GLARE` |
| Resolution | Width/height minimum | < 64px → fail | `IMAGE_TOO_SMALL` |
| Decode | Pillow decode attempt | Failure → reject | `DECODE_FAILED` |

**Why this matters:**
- Blurry images destroy texture evidence — Laplacian variance drops below threshold
- Glare from specular reflection hides material detail under white patches
- Under/overexposure distorts the luminance distribution that embeddings depend on
- Inconsistent capture quality creates false model behavior — the model may learn
  "camera artifacts" instead of "material signatures"

Images that fail quality are logged, and their raw evidence is preserved. They should
not advance through the standard normalization/embedding path. The current implementation
does not publish a downstream event for failed images, but the raw file remains
accessible for manual review or re-assessment if quality thresholds are later adjusted.

---

## 7. Normalization Technology

Raw captured images vary in orientation, color mode, aspect ratio, and resolution.
The normalization service creates a standardized derivative suitable for embedding.

**Current normalization** (implemented in `auth_common.imaging.normalize_image`):

1. **EXIF orientation correction** — rotates based on camera EXIF metadata
2. **RGB conversion** — converts grayscale, RGBA, or other modes to 3-channel RGB
3. **Center crop to square** — takes the largest centered square region
4. **Resize to 512×512** — bilinear/Lanczos downsampling
5. **Output as PNG** — lossless format for the model-ready derivative

**The raw image is never modified.** It is preserved separately from normalized
derivatives under a stable S3 object key. The current local implementation relies on
object key conventions and application-level policy to maintain this separation.
Production-grade immutability enforcement (e.g., S3 Object Lock) is future work.

```text
Raw evidence:    s3://auth-platform-raw-evidence/scans/{org}/{session}/raw/{id}.jpg
Normalized:      s3://auth-platform-normalized-evidence/{session}/{id}_normalized.png
```

---

## 8. Baseline Texture Embeddings

`texture_baseline_v0.1.0` is a deterministic, hand-crafted feature extraction pipeline
that produces a 128-dimensional vector from a normalized image. It does **not** use
neural networks or learned weights.

**Feature composition:**

| Feature Group | Method | Bins | Purpose |
|---|---|---|---|
| Grayscale intensity | Histogram of pixel values | 32 | Overall brightness distribution |
| Color channels | Per-channel (B, G, R) histograms | 3 × 16 = 48 | Color distribution |
| Edge/gradient | Sobel magnitude histogram | 32 | Texture edge density |
| Local variance | Box-filter variance histogram | 16 | Micro-texture roughness |
| **Total** | | **128** | |

The resulting vector is **L2-normalized to unit length** and stored in pgvector.

**Why this baseline exists:**
- Provides immediate non-ML embedding behavior for pipeline validation
- Works well on synthetic separable texture groups (100% NN agreement)
- Provides a comparison target for learned metric models
- Does **not** prove real authentication accuracy — it is a floor, not a ceiling

---

## 9. Learned Metric Embeddings

`learned_metric_v0.1.0` is a **lifecycle scaffold** — a PyTorch metric-learning model
that exists to validate the training → export → register → re-embed → evaluate pipeline.
It is not a representative learned model and its performance should not be compared
meaningfully against the hand-crafted baseline.

**Architecture:**
- **Backbone:** ResNet18 (randomly initialized by default; ImageNet pretrained optional)
- **Projection head:** Linear(512 → 256) → ReLU → Linear(256 → 128)
- **Output:** 128-dimensional L2-normalized embedding
- **Input:** 224×224 RGB (resized from 512×512 normalized images)

**Training:**
- **Loss:** Contrastive loss with configurable margin
- **Pairs:** Positive pairs (same class) and negative pairs (different class)
- **Data:** Loaded from governed reference datasets via `reference_dataset_members`
- **Splits:** Only `train` split images with `include_in_training=TRUE` are used
- **Validation:** Monitored on `validation` split

**Why it underperforms the baseline:** 10 epochs on 18 synthetic images with a randomly
initialized ResNet18 cannot learn useful texture representations. This is expected and
is not a meaningful baseline-vs-learned comparison — it only proves that the ML lifecycle
machinery works. A meaningful learned model requires a pretrained backbone, real governed
datasets, and substantially more training data. See
[ADR-0002](../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md)
for the embedding dimension and backbone decision that must be made before serious
learned-model training.

**Future embedding dimensions:** Production learned embeddings may need 512 or 768
dimensions rather than 128. Changing embedding dimension after a large reference library
is built requires re-embedding all references, so this decision should be made before
committing to large-scale real reference embeddings.

**Model artifacts:**
- Exported to S3: `s3://auth-platform-ml-artifacts/models/{version}/model.pt`
- Metadata JSON alongside: `models/{version}/metadata.json`
- Registered in `model_versions` table with artifact URI and version info

---

## 10. Metric Learning Explained

Metric learning trains a model to map images into an **embedding space** where similar
items are close together and dissimilar items are far apart, measured by cosine similarity.

### Embeddings

An embedding is a dense vector (e.g., 128 floats) that represents an image's content
in a way that preserves meaningful similarity. Two images with similar textures should
produce vectors that are close in cosine distance.

### Cosine Similarity

```
similarity(A, B) = dot(A, B) / (|A| × |B|)
```

For unit-normalized vectors (as LuxAuth uses), this simplifies to the dot product.
Values range from -1 (opposite) to +1 (identical). The current local scoring rules
use these approximate ranges, which are **global development defaults** and not validated
production thresholds. Future thresholds should be scoped by brand, material, and region
when real data exists — a threshold that works for leather grain may not work for hardware
engraving:
- \> 0.85: strong match
- 0.50–0.85: moderate similarity
- < 0.50: low similarity or mismatch

### Contrastive Loss

The training objective pulls positive pairs together and pushes negative pairs apart:

```
positive pair (same class):   loss = distance²
negative pair (diff class):   loss = max(0, margin - distance)²
```

### Example

Consider three leather samples:

- **A**: Authentic cow leather, belly region
- **B**: Authentic cow leather, belly region (different sample)
- **C**: Counterfeit synthetic leather

After training, the model should produce:

```
similarity(A, B) ≈ 0.92   (high — both authentic cow belly)
similarity(A, C) ≈ 0.35   (low — authentic vs counterfeit)
```

### Why This Supports Growing Reference Libraries

When a new authenticated item is added to the reference library, its embedding is
computed once and stored. Future queries automatically compare against it via vector
search — no model retraining needed. The reference library grows incrementally.

---

## 11. Vector Search and Reference Matching

Embeddings are stored in **PostgreSQL with pgvector** and searched using the cosine
distance operator (`<=>`).

The vector-search-service applies multiple filters to ensure meaningful comparisons:

| Filter | Purpose |
|---|---|
| `embedding_model_version` | Only compare vectors from the same model |
| `region_code` | Like-for-like comparison (leather vs leather, not leather vs hardware) |
| `dataset_version` membership | Only search within active, non-retired datasets |
| `include_in_search = TRUE` | Only search against train/reference images, not test images |

**Cross-model comparisons are invalid.** A texture_baseline embedding cannot be
meaningfully compared to a learned_metric embedding — they occupy completely different
vector spaces.

**For authentication datasets** (with CONFIRMED_AUTHENTIC and CONFIRMED_COUNTERFEIT
labels), the search returns:
- **Nearest authentic references** (top-K by similarity)
- **Nearest counterfeit references** (top-K by similarity)
- **Authentic cluster score** (mean similarity to authentic neighbors)
- **Counterfeit cluster score** (mean similarity to counterfeit neighbors)
- **OOD score** (1 - max similarity, indicating out-of-distribution distance)

**For public external datasets** (with PUBLIC_DATASET_CLASS labels), the search still
runs but the authentic/counterfeit split is not meaningful. These datasets use class or
material labels (e.g., species, fabric type) and the diagnostic value comes from
nearest-neighbor consistency and embedding clustering, not from authentic-vs-counterfeit
scoring.

If no reference embeddings exist for the query's model version, the service falls back
to a stub with a logged warning.

---

## 12. Region-Level Scoring

The region-scoring-service converts vector search similarity scores into a categorical
region decision. The current thresholds are local rules of thumb chosen for conservative
behavior during development — they have not been validated on production data and will
need calibration once real microscope datasets are available:

| Condition | Decision |
|---|---|
| authentic ≥ 0.85 AND counterfeit < 0.50 | `STRONG_MATCH` |
| authentic ≥ 0.70 | `MODERATE_MATCH` |
| authentic ≥ 0.50 | `WEAK_MATCH` |
| counterfeit > authentic | `MISMATCH` |
| Otherwise | `INCONCLUSIVE` |

**A single region should never certify an item.** Authentication requires evidence from
multiple independent capture regions. A strong match on leather grain does not compensate
for a mismatch on hardware engraving.

---

## 13. Scan-Level Decisions

The decision-service aggregates region-level evidence into a final authentication
decision, applying completeness checks before scoring:

**Decision priority (evaluated in order):**

| Priority | Condition | Result | Reason |
|---|---|---|---|
| 1 | Decision already exists | Return existing | Idempotent |
| 2 | Missing required regions | `INCONCLUSIVE` | `MISSING_REQUIRED_REGIONS` |
| 3 | No region scores | `INCONCLUSIVE` | `NO_REGION_SCORES` |
| 4 | Any MISMATCH region | `UNVERIFIED` | `REGION_MISMATCH_DETECTED` |
| 5 | Counterfeit > authentic avg | `UNVERIFIED` | `COUNTERFEIT_SIMILARITY_EXCEEDS_AUTHENTIC` |
| 6 | All STRONG + auth ≥ 0.85 + counter < 0.40 | `VERIFIED` | `ALL_REGIONS_STRONG_MATCH` |
| 7 | Authentic avg ≥ 0.60 | `EXPERT_REVIEW_REQUIRED` | `MODERATE_MATCH_REQUIRES_REVIEW` |
| 8 | Otherwise | `INCONCLUSIVE` | `INSUFFICIENT_SIMILARITY` |

Required regions come from scan recipes (e.g., the Louis Vuitton monogram canvas handbag
recipe requires EXTERIOR_CANVAS, FRONT_LOGO_PRINT, INTERIOR_HEAT_STAMP,
HARDWARE_ENGRAVING, and STITCHING_DETAIL). An incomplete scan always returns INCONCLUSIVE.

**Capture sessions are not automatically authentication decisions.** The capture-intake-service
manages capture lifecycle (CREATED → CAPTURING → COMPLETE/INCOMPLETE). Bridging a
completed capture to an authentication scan session is a separate, explicit step.

---

## 14. Dataset Governance

LuxAuth implements database-backed dataset governance to ensure reproducible, auditable
ML workflows.

**Core governance tables:**

| Table | Purpose |
|---|---|
| `reference_dataset_versions` | Named dataset versions with status lifecycle (draft → active → retired) |
| `reference_dataset_members` | Links images to datasets with train/validation/test splits |
| `reference_label_reviews` | Label provenance: who labeled, confidence, method |
| `threshold_profiles` | Scoring thresholds tied to model + dataset versions |
| `training_runs` | Training metadata, config, and metrics |
| `model_versions` | Model registry with artifact URIs |
| `evaluation_runs` | Evaluation metadata and summary metrics |
| `evaluation_items` | Per-image evaluation results |

**Default split policy** (current implementation; may be adjusted per dataset):

| Split | include_in_search | include_in_evaluation | include_in_training |
|---|---|---|---|
| train | TRUE | FALSE | TRUE |
| validation | FALSE | TRUE | FALSE |
| test | FALSE | TRUE | FALSE |
| holdout | FALSE | FALSE | FALSE |

**Leakage prevention:**
- All images from the same physical item (`reference_item_id` / `external_item_id`)
  must remain in the same split — this is the fundamental intra-item leakage rule
- Duplicate SHA-256 checksums across train/test splits are flagged
- Perceptual hash duplicates are warned when available
- Splits are assigned by item/sample, never by individual image
- Planned: enforce this as a hard validation failure during dataset promotion, not just
  a convention (see [ML Improvement Roadmap](roadmaps/ml-improvement-roadmap.md))

---

## 15. Public External Datasets

Public texture/material datasets are used to validate pipeline behavior on real images
before microscope captures are available.

| Dataset | Images | Content | LuxAuth Region Code |
|---|---|---|---|
| LeaData V1 | 1,200 | Microscopic leather (4 species × 300) | `EXTERNAL_LEATHER_TEXTURE` |
| FabricNET | 130 | Microscopic woven fabric | `EXTERNAL_FABRIC_TEXTURE` |

**What they validate:**
- Image ingestion, quality checks, and normalization on real microscopic images
- Texture embedding generation and pgvector storage
- Nearest-neighbor search behavior (do similar textures find each other?)
- Evaluation harness and diagnostic tools on non-trivial datasets
- Metric-learning training lifecycle with real images

**What they do NOT validate:**
- Authentic vs. counterfeit luxury goods discrimination
- Real-world authentication accuracy
- Microscope capture protocol behavior
- Production deployment readiness

External dataset images are stored locally under `datasets/external/` (gitignored) and
are never committed. License, citation, and commercial-use review is required for each
dataset — recorded in manifest YAML files.

---

## 16. Evaluation Harness

Evaluation runs compare expected labels to predicted outcomes for a specific combination
of dataset version, embedding model, and threshold profile.

**Metrics computed:**

| Metric | Definition |
|---|---|
| True positive | Authentic expected, system predicts VERIFIED |
| True negative | Counterfeit expected, system predicts UNVERIFIED |
| False positive | Counterfeit expected, system predicts VERIFIED |
| False negative | Authentic expected, system predicts UNVERIFIED |
| Inconclusive | System cannot determine (tracked separately) |
| Expert review | System requests human review (tracked separately) |

For external public datasets where labels are material class or species rather than
authentic/counterfeit, the evaluation framework still runs but produces all-INCONCLUSIVE
results (expected). The meaningful signal comes from embedding diagnostics and
nearest-neighbor inspection rather than the auth-specific metrics.

**Tools:**
- `run_evaluation.py` — creates evaluation run with per-item results
- `print_evaluation_report.py` — human-readable report with confusion matrix
- `compare_evaluations.py` — side-by-side multi-model comparison

---

## 17. Diagnostics and Calibration

Diagnostic tools make model behavior explainable before attempting tuning.

| Tool | Purpose |
|---|---|
| `analyze_embeddings.py` | Distribution stats, cluster separation, NN label agreement |
| `inspect_neighbors.py` | Per-image top-K neighbor analysis with JSON export |
| `calibrate_thresholds.py` | Threshold sweep (49 combinations), conservative/balanced profiles |
| `export_embedding_projection.py` | PCA 2D projection CSV for external visualization |
| `compare_evaluations.py` | Multi-model metric comparison table |

**Why diagnostics matter:**
- **Embedding collapse** — if all vectors converge, similarity is meaningless
- **NN mistakes** — reveal which images confuse the model
- **Threshold sensitivity** — show how small threshold changes affect FP/FN rates
- **Cluster separation** — quantifies whether authentic/counterfeit (or class) groups are distinguishable (texture_baseline achieves 0.617 separation on synthetic data; learned_metric achieves 0.002 — explaining the performance gap)
- **OOD behavior** — identifies images that match nothing in the reference library

---

## 18. Why SageMaker Is Deferred

The current system uses local Python/FastAPI containers for all ML inference and training.
SageMaker is not rejected — it is **deferred until real operational need justifies it**.

**Current situation:**
- Model lifecycle is not stable (still validating baseline vs. learned approaches)
- Throughput requirements are unknown (no production traffic)
- Debugging is easier with local containers than managed endpoints
- The evidence pipeline, dataset governance, and evaluation harness are the current priority

**SageMaker may be added later for:**
- Managed GPU training jobs
- Model registry and approval workflows
- Real-time or async inference endpoints with autoscaling
- Batch re-embedding of large reference libraries
- ML governance and lineage tracking

See [ADR-0001](../auth-platform/docs/architecture/adr-0001-defer-sagemaker.md) for the
full rationale and revisit criteria.

---

## 19. Future Mobile Capture Clients

`iphone-app/` and `android-app/` are peer directories beside `auth-platform/` for future
capture clients.

The backend is **device-agnostic by design**:
- The `capture-intake-service` accepts images and metadata via HTTP APIs
- Device-specific microscope control (USB, Bluetooth, vendor SDKs) belongs in the client
- The backend validates images, stores evidence, and runs the pipeline
- Capture sessions create canonical `image_assets` entries, so uploaded captures enter
  the same pipeline as scan uploads and batch-ingested images

---

## 20. Current Limitations

- **No production authentication claims.** The system is a local MVP/prototype.
- **No verified luxury microscope dataset.** Synthetic and public datasets validate
  pipeline behavior, not authentication accuracy.
- **No real microscope calibration data.** Device calibration APIs exist but no real
  calibration profiles have been created.
- **No production auth/security layer.** No JWT authentication, RBAC, or rate limiting.
- **No cloud infrastructure-as-code.** Terraform/CDK deferred until AWS deployment.
- **Learned model is a lifecycle scaffold only** — learned_metric_v0.1.0 validates the
  ML pipeline machinery, not learned embedding quality. Its underperformance versus the
  baseline is not a meaningful comparison.
- **Public datasets validate texture behavior only**, not luxury goods discrimination.
- **No object-lock or immutability enforcement** beyond S3 key conventions and
  application-level controls.
- **No item condition or repair metadata.** Real luxury items may have known repairs,
  replaced components, or third-party restoration that affect region-level evidence.
  Condition tracking and repair-aware routing to expert review are planned
  (see [ML Improvement Roadmap](roadmaps/ml-improvement-roadmap.md)).
- **OOD detection is a simple similarity-derived proxy** (`1 - max_similarity`), not a
  full OOD detector. More robust methods (Mahalanobis distance, kNN density, Isolation
  Forest) require larger reference datasets and are planned as a separate roadmap item.
- **Center-crop normalization may discard edge texture** from rectangular microscope
  captures. Multi-crop and padded-resize alternatives are planned for evaluation.
- **Queue-driven pipeline is not latency-optimized** for real-time mobile use. Result
  orchestration (polling, webhooks, synchronous fast-path) is future product work.
- **No adversarial robustness analysis.** The system has not been evaluated against
  adversarial inputs, counterfeit-aware evasion, or deliberately crafted images. A threat
  model for adversarial robustness is future work.
- **Patch-based or multi-crop embedding may be necessary** before large reference
  libraries are built. The current center-crop approach processes one global view per
  image; patch-level embeddings could capture region detail that center-crop misses.
  See [Patch-Based Region Embedding](../auth-platform/docs/architecture/patch-based-region-embedding.md).
- **Embedding dimension is locked at 128** for both baseline and learned models. Production
  learned embeddings may need 512–768 dimensions. Changing dimension after reference
  library growth requires full re-embedding.
  See [ADR-0002](../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md).
- **Verified data is the strategic bottleneck**, not architecture. See
  [Dataset Acquisition Strategy](roadmaps/dataset-acquisition-strategy.md).

---

## 21. Roadmap Toward Real Authentication

| Stage | Description |
|---|---|
| 1 | Public external dataset evaluation (current) |
| 2 | Microscope acceptance testing (runbook ready) |
| 3 | Controlled lab capture batches (framework ready) |
| 4 | Dataset promotion and baseline evaluation |
| 5 | Learned model training on real data |
| 6 | Baseline vs. learned model comparison |
| 7 | Region-specific models and auxiliary classifiers |
| 8 | Human review workbench |
| 9 | Cloud deployment and security hardening |
| 10 | SageMaker or dedicated inference serving (if warranted) |
| 11 | Production validation with sufficient labeled real data |

Each stage builds on governed datasets, reproducible evaluation, and conservative
decision rules. The system is designed to prove capability incrementally, not to
ship prematurely.

---

## 22. Glossary

| Term | Definition |
|---|---|
| **Raw evidence** | The original uploaded image file, preserved in S3 separately from derivatives |
| **Normalized derivative** | A standardized 512×512 RGB PNG created from raw evidence |
| **Embedding** | A dense vector (128 floats) representing an image's content |
| **Metric learning** | Training a model to place similar items close in embedding space |
| **Contrastive loss** | A loss function that pulls positives together and pushes negatives apart |
| **Vector search** | Finding nearest neighbors in embedding space using cosine similarity |
| **pgvector** | PostgreSQL extension for storing and querying vector embeddings |
| **Dataset version** | A named, governed collection of reference images with splits |
| **Label provenance** | Record of who labeled an image, their confidence, and method |
| **Threshold profile** | A set of scoring thresholds tied to a model and dataset version |
| **OOD (out-of-distribution)** | An image that does not match any known reference cluster |
| **Scan recipe** | Defines which capture regions are required for a product type |
| **Capture protocol** | Defines region requirements for live capture sessions |
| **Capture session** | A live API-driven capture workflow (device → backend) |
| **Capture batch** | A manifest-driven offline ingestion workflow (lab → backend) |
| **Reference image** | A labeled image in the reference library used for comparison |
| **Reference item** | A physical item from which reference images were captured |

---

## 23. Related Documents

- [Repository README](../README.md)
- [Development Roadmap](roadmap.md)
- [ML Improvement Roadmap](roadmaps/ml-improvement-roadmap.md)
- [Public Dataset Evaluation Plan](datasets/public-dataset-evaluation-plan.md)
- [Dataset Storage Policy](datasets/dataset-storage-policy.md)
- [External Dataset First Run Results](datasets/external-dataset-first-run-results.md)
- [Microscope Acceptance Runbook](operations/microscope-acceptance-runbook.md)
- [Capture Quality Guide](operations/capture-quality-guide.md)
- [Service Catalog](../auth-platform/docs/service-catalog.md)
- [Service Interactions](../auth-platform/docs/service-interactions.md)
- [Event Flow](../auth-platform/docs/architecture/event-flow.md)
- [Service Boundaries](../auth-platform/docs/architecture/service-boundaries.md)
- [ADR-0001: Defer SageMaker](../auth-platform/docs/architecture/adr-0001-defer-sagemaker.md)
- [ADR-0002: Embedding Dimension and Backbone](../auth-platform/docs/architecture/adr-0002-learned-embedding-dimension-and-backbone.md)
- [Patch-Based Region Embedding](../auth-platform/docs/architecture/patch-based-region-embedding.md)
- [Dataset Acquisition Strategy](roadmaps/dataset-acquisition-strategy.md)
- [Phase 4: Real Image Baseline](../auth-platform/docs/architecture/phase-4-real-image-baseline.md)
- [Phase 5: Dataset Governance](../auth-platform/docs/architecture/phase-5-dataset-governance-evaluation.md)
- [Phase 7: ML Diagnostics](../auth-platform/docs/architecture/phase-7-ml-diagnostics-calibration.md)
