# Event Flow

## Pipeline Overview

When a user uploads a microscopic image, it flows through a series of processing stages. Each stage is triggered by an event from the previous stage, published via SQS.

```
 Mobile App / API Client
        │
        ▼
 ┌──────────────────────┐
 │ evidence-asset-service│  POST /scan-sessions/{id}/images
 │       (8104)          │
 └──────────┬───────────┘
            │ ImageUploaded
            ▼
 ┌──────────────────────┐
 │ image-quality-service │  Assess sharpness, blur, lighting
 │       (8201)          │
 └──────────┬───────────┘
            │ ImageQualityCompleted  (pass/fail + metrics)
            ▼
 ┌──────────────────────┐
 │ normalization-service │  Crop, resize, color-correct
 │       (8202)          │
 └──────────┬───────────┘
            │ ImageNormalized  (normalized S3 key)
            ▼
 ┌──────────────────────┐
 │  embedding-service    │  Generate vector embedding
 │       (8203)          │
 └──────────┬───────────┘
            │ EmbeddingGenerated  (embedding vector)
            ▼
 ┌──────────────────────┐
 │ vector-search-service │  Search reference DB (pgvector)
 │       (8204)          │
 └──────────┬───────────┘
            │ VectorSearchCompleted  (top-K matches + distances)
            ▼
 ┌──────────────────────┐
 │ region-scoring-service│  Score region authenticity
 │       (8205)          │
 └──────────┬───────────┘
            │ RegionScored  (score + confidence)
            ▼
 ┌──────────────────────┐
 │  decision-service     │  Aggregate scores → verdict
 │       (8301)          │
 └──────────┬───────────┘
            │ AuthenticationDecisionCreated
            ▼
      AUTHENTIC / SUSPECT / INCONCLUSIVE
```

## Event Types

| Event | Producer | Consumer | Queue | Payload (key fields) |
|---|---|---|---|---|
| ImageUploaded | evidence-asset-service | image-quality-service | `image-uploaded` | image_id, s3_key, scan_session_id, region_code |
| ImageQualityCompleted | image-quality-service | normalization-service | `image-quality-completed` | image_id, passed, sharpness, blur_score |
| ImageNormalized | normalization-service | embedding-service | `image-normalized` | image_id, normalized_s3_key |
| EmbeddingGenerated | embedding-service | vector-search-service | `embedding-generated` | image_id, embedding_vector (or ref) |
| VectorSearchCompleted | vector-search-service | region-scoring-service | `vector-search-completed` | image_id, matches[ {ref_id, distance} ] |
| RegionScored | region-scoring-service | decision-service | `region-scored` | image_id, scan_session_id, region_code, score, confidence |
| AuthenticationDecisionCreated | decision-service | review-service, certificate-service | `authentication-decision-created` | scan_session_id, verdict, confidence, region_scores |

## Queue Assignments

Each event type maps to a dedicated SQS queue. Dead-letter queues (DLQ) are configured for each with a max receive count of 3 before messages are moved to the DLQ for investigation.

## Notes

- If `ImageQualityCompleted` reports a failure (image too blurry, etc.), the pipeline stops for that image. The scan session may still proceed if other region images pass.
- The decision-service waits until all required regions for a scan session have been scored before producing a verdict.
- `AuthenticationDecisionCreated` fans out to both review-service (for low-confidence routing) and certificate-service (for high-confidence issuance).
