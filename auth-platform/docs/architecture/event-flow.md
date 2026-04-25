# Event Flow

## Pipeline Architecture

The authentication pipeline is event-driven. Each processing stage consumes messages from an SQS queue,
performs its work, and publishes to the next queue.

```text
evidence-asset-service
  │ publishes IMAGE_UPLOADED
  ▼
image-quality-queue
  │ consumed by image-quality-service worker
  │ publishes IMAGE_QUALITY_COMPLETED
  ▼
normalization-queue
  │ consumed by normalization-service worker
  │ publishes IMAGE_NORMALIZED
  ▼
embedding-queue
  │ consumed by embedding-service worker
  │ publishes EMBEDDING_GENERATED
  ▼
vector-search-queue
  │ consumed by vector-search-service worker
  │ publishes VECTOR_SEARCH_COMPLETED
  ▼
region-scoring-queue
  │ consumed by region-scoring-service worker
  │ publishes REGION_SCORED
  ▼
decision-queue
  │ consumed by decision-service worker
  │ checks if all required regions are scored
  │ if complete → creates AUTHENTICATION_DECISION
  ▼
authentication_decisions table
```

## Event Types

| Event Type | Producer | Consumer Queue | Consumer Service |
|---|---|---|---|
| IMAGE_UPLOADED | evidence-asset-service | image-quality-queue | image-quality-service |
| IMAGE_QUALITY_COMPLETED | image-quality-service | normalization-queue | normalization-service |
| IMAGE_NORMALIZED | normalization-service | embedding-queue | embedding-service |
| EMBEDDING_GENERATED | embedding-service | vector-search-queue | vector-search-service |
| VECTOR_SEARCH_COMPLETED | vector-search-service | region-scoring-queue | region-scoring-service |
| REGION_SCORED | region-scoring-service | decision-queue | decision-service |
| AUTHENTICATION_DECISION_CREATED | decision-service | — | — |
| PROCESSING_FAILED | any service | — | audit trail |

## Event Envelope

All events use a standard `EventEnvelope`:

```json
{
  "event_id": "uuid",
  "event_type": "image.quality_completed",
  "correlation_id": "uuid",
  "tenant_id": "uuid",
  "scan_session_id": "uuid",
  "image_id": "uuid",
  "region_code": "EXTERIOR_CANVAS",
  "source_service": "image-quality-service",
  "schema_version": "1.0",
  "timestamp": "2026-04-25T12:00:00Z",
  "payload": { ... }
}
```

## Idempotency

Each processing stage uses an idempotency key to prevent duplicate processing:

| Stage | Key Components |
|---|---|
| IMAGE_QUALITY | image_id + stage + quality_model_version |
| NORMALIZATION | image_id + stage + preprocessing_version |
| EMBEDDING | image_id + stage + embedding_model_version |
| VECTOR_SEARCH | image_id + stage + reference_dataset_version + embedding_model_version |
| REGION_SCORING | image_id + stage + scoring_rule_version |
| DECISION | scan_session_id + stage + decision_rule_version |

Duplicate messages are detected via the `processing_runs` table and safely skipped.

## Dead Letter Queue

All processing queues are configured with a redrive policy pointing to `dead-letter-queue` after 3 failed receives. Failed processing also records a `PROCESSING_FAILED` audit event.

## Correlation IDs

Every request and event carries a `correlation_id` (UUID). If not provided, one is generated at the entry point. The correlation ID flows through:
- HTTP request headers (`X-Correlation-ID`)
- SQS event envelopes
- Structured log entries
- Audit event records
