# Service Catalog

One-page reference for all backend microservices.

## Services

| Service | Port | Domain | Primary Responsibility | Consumes Queue | Publishes To | Main Tables | Notes |
|---|---|---|---|---|---|---|---|
| scan-session-service | 8101 | Operational | Create/manage auth scan sessions | — | — | scan_sessions, scan_recipe_regions | Calls scan-recipe-service via HTTP |
| scan-recipe-service | 8102 | Operational | Serve scan recipe definitions | — | — | scan_recipes, scan_recipe_regions | Read-only; recipes seeded via SQL |
| device-service | 8103 | Operational | Device registration + calibration | — | — | devices, device_calibrations | |
| evidence-asset-service | 8104 | Evidence | Raw image intake for scan sessions | — | image-quality-queue | image_assets, scan_sessions | Validates images, stores in S3 |
| capture-intake-service | 8106 | Capture | Device-agnostic capture sessions | — | image-quality-queue | capture_protocols, capture_sessions, capture_session_images | Protocol-driven region completeness |
| image-quality-service | 8201 | Pipeline | Image quality assessment (OpenCV) | image-quality-queue | normalization-queue | image_quality_reports | Sharpness, exposure, glare |
| normalization-service | 8202 | Pipeline | 512x512 RGB PNG normalization | normalization-queue | embedding-queue | normalized_images | EXIF fix, center-crop, resize |
| embedding-service | 8203 | Pipeline | Vector embedding generation | embedding-queue | vector-search-queue | embeddings, model_versions | Supports texture_baseline + learned_metric |
| vector-search-service | 8204 | Pipeline | pgvector cosine similarity search | vector-search-queue | region-scoring-queue | reference_embeddings, embeddings | Filters by region, model version, dataset |
| region-scoring-service | 8205 | Pipeline | Region-level auth scoring | region-scoring-queue | decision-queue | region_scores | STRONG_MATCH through MISMATCH |
| decision-service | 8301 | Trust | Final authentication decision | decision-queue | — | authentication_decisions, scan_sessions | Completeness-aware; updates session status |
| review-service | 8302 | Trust | Human expert review queue | — | — | review_cases | Skeleton implementation |
| certificate-service | 8303 | Trust | Issue auth certificates | — | — | certificates, authentication_decisions | Only for VERIFIED decisions |

## Queue Chain

```text
evidence-asset-service / capture-intake-service
  → image-quality-queue → image-quality-service
  → normalization-queue → normalization-service
  → embedding-queue → embedding-service
  → vector-search-queue → vector-search-service
  → region-scoring-queue → region-scoring-service
  → decision-queue → decision-service
```

## S3 Buckets

| Bucket | Purpose | Writers |
|---|---|---|
| auth-platform-raw-evidence | Immutable raw images | evidence-asset-service, capture-intake-service |
| auth-platform-normalized-evidence | 512x512 PNG derivatives | normalization-service |
| auth-platform-reference-library | Reference images + lab captures | ingestion scripts |
| auth-platform-ml-artifacts | Model artifacts (model.pt, metadata.json) | training scripts |

## Audit Events

| Event Type | Source |
|---|---|
| SCAN_CREATED | scan-session-service |
| DEVICE_REGISTERED | device-service |
| DEVICE_CALIBRATION_CREATED | device-service |
| IMAGE_UPLOADED | evidence-asset-service |
| CAPTURE_PROTOCOL_CREATED | capture-intake-service |
| CAPTURE_SESSION_CREATED | capture-intake-service |
| CAPTURE_SESSION_IMAGE_UPLOADED | capture-intake-service |
| CAPTURE_SESSION_COMPLETED | capture-intake-service |
| CAPTURE_SESSION_INCOMPLETE | capture-intake-service |
| IMAGE_QUALITY_COMPLETED | image-quality-service |
| IMAGE_NORMALIZED | normalization-service |
| EMBEDDING_GENERATED | embedding-service |
| VECTOR_SEARCH_COMPLETED | vector-search-service |
| REGION_SCORED | region-scoring-service |
| DECISION_CREATED | decision-service |
