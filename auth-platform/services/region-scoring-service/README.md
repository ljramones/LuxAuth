# Region Scoring Service

## Purpose

Converts vector search similarity scores into authentication region decisions. Each image region (e.g., logo, stitching, hardware) receives a discrete match classification based on its authentic and counterfeit similarity scores. These per-region decisions feed into the final authentication decision.

## Responsibilities

- Accept similarity scores from vector search results.
- Apply threshold-based decision rules to classify each region.
- Persist region scores to the `region_scores` table.
- Publish scored regions to the decision queue.

## Non-Responsibilities

- Does not perform vector similarity search (see vector-search-service).
- Does not aggregate region scores into a final authentication decision (see decision-service).
- Does not define which regions are required for a given item type (see scan-recipe-service).

## Runtime

| Property | Value |
|---|---|
| Port | `8205` |
| Healthcheck | `GET /health` |
| Readiness | `GET /ready` |
| Worker queue | `region-scoring-queue` |
| Framework | FastAPI |

## Main APIs

### POST /score

Score a single image region.

**Request**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "scan_session_id": "sess_abc123",
  "region_code": "logo_front",
  "authentic_similarity": 0.90,
  "counterfeit_similarity": 0.35,
  "ood_score": 0.12
}
```

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "scan_session_id": "sess_abc123",
  "region_code": "logo_front",
  "decision": "STRONG_MATCH",
  "authentic_similarity": 0.90,
  "counterfeit_similarity": 0.35
}
```

### GET /scores/{scan_session_id}

Retrieve all region scores for a scan session.

**Response 200**

```json
{
  "scan_session_id": "sess_abc123",
  "scores": [
    {
      "region_code": "logo_front",
      "decision": "STRONG_MATCH",
      "authentic_similarity": 0.90,
      "counterfeit_similarity": 0.35
    },
    {
      "region_code": "stitching_side",
      "decision": "MODERATE_MATCH",
      "authentic_similarity": 0.74,
      "counterfeit_similarity": 0.28
    }
  ]
}
```

### GET /health

Returns `{"status": "ok"}` when the process is alive.

### GET /ready

Returns 200 when the service can reach the database and SQS.

## Decision Logic

The `ScoreRequest` includes `authentic_similarity`, `counterfeit_similarity`, and `ood_score`. The region decision is determined by the first matching rule:

| Rule | Condition | Decision |
|---|---|---|
| 1 | `authentic >= 0.85` AND `counterfeit < 0.50` | `STRONG_MATCH` |
| 2 | `authentic >= 0.70` | `MODERATE_MATCH` |
| 3 | `authentic >= 0.50` | `WEAK_MATCH` |
| 4 | `counterfeit > authentic` | `MISMATCH` |
| 5 | None of the above | `INCONCLUSIVE` |

Rules are evaluated in order; the first match wins.

## Events Consumed

| Event | Queue | Description |
|---|---|---|
| `VECTOR_SEARCH_COMPLETED` | `region-scoring-queue` | Triggers region scoring with similarity scores in the payload. |

## Events Published

| Event | Queue | Description |
|---|---|---|
| `REGION_SCORED` | `decision-queue` | Published after the region score is persisted. |

## Database Tables

| Table | Access | Purpose |
|---|---|---|
| `region_scores` | Write | Persist the region decision and similarity scores. |
| `image_assets` | Read | Look up the `region_code` for the image. |
| `processing_runs` | Read/Write | Idempotency tracking. |

## S3 Usage

This service does not access S3.

## Configuration

| Setting | Description |
|---|---|
| `sqs_region_scoring_queue` | SQS queue URL for incoming scoring requests. |
| `sqs_decision_queue` | SQS queue URL for publishing scored regions downstream. |

## Local Development

```bash
cd services/region-scoring-service

pip install -e ".[dev]"

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8205 --reload

# Run the worker
python -m app.worker
```

Requires PostgreSQL and LocalStack (or real AWS) for SQS.

## Observability

- Structured logs include `image_asset_id`, `scan_session_id`, `region_code`, and the computed `decision`.
- Audit event `REGION_SCORED` is recorded for every scored region.

## Idempotency

Key format: `{image_id}|REGION_SCORING|scoring_rules_v0.1.0`

Duplicate processing is prevented via the `processing_runs` table.

## Security Notes

- This service handles only numeric scores and string identifiers. No image data or PII flows through it.
- Threshold values are hardcoded in the scoring rules; they are not user-configurable via API.

## Current Limitations

- Scoring thresholds are hardcoded and global. There is no per-brand, per-item-type, or per-region threshold tuning.
- The `ood_score` is accepted in the request but does not currently influence the decision logic. It is stored for future use.
- `scoring_rules_v0.1.0` is the initial rule set. The version is tracked in idempotency keys so that reprocessing can be triggered when rules change.

## Related Documentation

- [Vector Search Service](../vector-search-service/README.md) -- preceding pipeline stage.
- [Decision Service](../decision-service/README.md) -- next pipeline stage that aggregates region scores.
