# Service Interactions

## 1. Authentication Scan Flow

The primary pipeline for authenticating a product.

```text
Client
  │ POST /scan-sessions
  ▼
scan-session-service (8101)
  │ calls scan-recipe-service via HTTP
  │ creates scan_sessions record
  │ returns required_regions
  ▼
Client
  │ POST /scan-sessions/{id}/images (per region)
  ▼
evidence-asset-service (8104)
  │ validates image + region code
  │ stores raw image in S3
  │ publishes IMAGE_UPLOADED to image-quality-queue
  ▼
image-quality-service (8201)  [worker]
  │ downloads raw image from S3
  │ computes sharpness, exposure, glare
  │ if PASS → publishes IMAGE_QUALITY_COMPLETED to normalization-queue
  │ if FAIL → pipeline stops for this image
  ▼
normalization-service (8202)  [worker]
  │ downloads raw image from S3
  │ EXIF fix → RGB → center-crop → 512x512 → PNG
  │ uploads to normalized-evidence bucket
  │ publishes IMAGE_NORMALIZED to embedding-queue
  ▼
embedding-service (8203)  [worker]
  │ downloads normalized PNG from S3
  │ generates 128-dim embedding (texture_baseline or learned_metric)
  │ stores vector in pgvector
  │ publishes EMBEDDING_GENERATED to vector-search-queue
  ▼
vector-search-service (8204)  [worker]
  │ queries pgvector for nearest reference embeddings
  │ filters by region_code, model_version, dataset membership
  │ computes authentic/counterfeit cluster scores
  │ publishes VECTOR_SEARCH_COMPLETED to region-scoring-queue
  ▼
region-scoring-service (8205)  [worker]
  │ converts similarity scores to region decision
  │ STRONG_MATCH / MODERATE_MATCH / WEAK_MATCH / MISMATCH / INCONCLUSIVE
  │ publishes REGION_SCORED to decision-queue
  ▼
decision-service (8301)  [worker]
  │ checks if ALL required regions are scored
  │ if not → waits (does not create decision)
  │ if all scored → aggregates scores
  │ checks completeness, mismatch, thresholds
  │ creates authentication_decisions record
  │ updates scan_sessions.status
  ▼
Result: VERIFIED / UNVERIFIED / INCONCLUSIVE / EXPERT_REVIEW_REQUIRED
```

## 2. Live Capture Intake Flow

For API-driven capture via mobile app or desktop client.

```text
Capture Client
  │ POST /devices/register (once)
  │ POST /devices/{id}/calibrations (once)
  ▼
device-service (8103)
  ▼
Capture Client
  │ GET /capture-protocols/{code}
  │ POST /capture-sessions
  │ POST /capture-sessions/{id}/images (per region, per image)
  │ GET /capture-sessions/{id}/status (check completeness)
  │ POST /capture-sessions/{id}/complete
  ▼
capture-intake-service (8106)
  │ validates protocol, region codes, images
  │ stores in S3
  │ publishes IMAGE_UPLOADED to image-quality-queue
  ▼
(same pipeline as authentication scan flow from image-quality-service onward)
```

## 3. Manifest/Lab Capture Batch Flow

Offline, script-driven ingestion of microscope images.

```text
Operator
  │ captures images with microscope
  │ organizes into folder + manifest.yaml
  ▼
scripts/generate_lab_capture_batch.py (or manual)
  ▼
scripts/validate_capture_batch.py --batch {code}
  │ validates manifest, protocol, images, quality
  │ creates capture_batches, capture_batch_items, capture_batch_images
  │ creates validation report
  ▼
scripts/ingest_capture_batch.py --batch {code}
  │ uploads raw images to S3
  │ normalizes images
  │ creates reference_items, reference_images, label_reviews
  ▼
scripts/promote_capture_batch_to_dataset.py --batch {code} --dataset {version}
  │ creates/updates dataset version
  │ assigns train/validation/test splits by item
  │ generates embeddings
  │ runs leakage checks
  ▼
scripts/reembed_reference_dataset.py --model {version}
scripts/run_evaluation.py --model {version}
scripts/print_evaluation_report.py
```

## 4. ML Lifecycle Flow

Local training and evaluation workflow.

```text
Dataset (reference_dataset_versions)
  │ contains reference images with train/val/test splits
  ▼
scripts/train_model.py --epochs 10
  │ loads train split from DB + S3
  │ trains ResNet18 + contrastive loss
  │ exports model.pt + metadata.json to S3
  │ registers model_versions record
  ▼
scripts/reembed_reference_dataset.py --model learned_metric_v0.1.0
  │ re-embeds all reference images with new model
  ▼
scripts/run_evaluation.py --model learned_metric_v0.1.0
  │ evaluates test split against search references
  │ records evaluation_runs + evaluation_items
  ▼
scripts/print_evaluation_report.py
scripts/compare_evaluations.py
scripts/analyze_embeddings.py --model learned_metric_v0.1.0
scripts/inspect_neighbors.py --model learned_metric_v0.1.0
scripts/calibrate_thresholds.py --model learned_metric_v0.1.0
```

## HTTP Dependencies Between Services

| Caller | Calls | Purpose |
|---|---|---|
| scan-session-service | scan-recipe-service | Recipe resolution |

All other inter-service communication is via SQS queues (async, event-driven).
