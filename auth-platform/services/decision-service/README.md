# Decision Service

## Purpose

Aggregates per-region scores into a final authentication decision with completeness checks. This is the terminal stage of the authentication pipeline. It waits until all required regions are scored, then applies a rule-based decision engine to produce one of four outcomes: `VERIFIED`, `UNVERIFIED`, `EXPERT_REVIEW_REQUIRED`, or `INCONCLUSIVE`.

## Responsibilities

- Check whether all required regions for a scan session have been scored.
- Apply the decision rule engine to aggregate region scores.
- Persist the authentication decision with a detailed summary.
- Update the scan session status to reflect the decision outcome.

## Non-Responsibilities

- Does not score individual regions (see region-scoring-service).
- Does not define which regions are required (see scan-recipe-service).
- Does not handle expert review workflows (see review-service).

## Runtime

| Property | Value |
|---|---|
| Port | `8301` |
| Healthcheck | `GET /health` |
| Readiness | `GET /ready` |
| Worker queue | `decision-queue` |
| Framework | FastAPI |

## Main APIs

### POST /decide/{scan_session_id}

Trigger a decision for a scan session. If not all required regions are scored yet, returns `INCONCLUSIVE` with reason `MISSING_REQUIRED_REGIONS`.

**Request**

```
POST /decide/sess_abc123
```

**Response 200**

```json
{
  "scan_session_id": "sess_abc123",
  "decision_result": "VERIFIED",
  "decision_reason": "ALL_REGIONS_STRONG_MATCH",
  "summary": {
    "required_region_count": 3,
    "completed_region_count": 3,
    "missing_regions": [],
    "all_required_regions_satisfied": true,
    "result_reason": "ALL_REGIONS_STRONG_MATCH"
  },
  "created_at": "2026-04-24T10:20:00Z"
}
```

**Response 200 (review needed)**

```json
{
  "scan_session_id": "sess_abc123",
  "decision_result": "EXPERT_REVIEW_REQUIRED",
  "decision_reason": "MODERATE_MATCH_REQUIRES_REVIEW",
  "summary": {
    "required_region_count": 3,
    "completed_region_count": 3,
    "missing_regions": [],
    "all_required_regions_satisfied": true,
    "result_reason": "MODERATE_MATCH_REQUIRES_REVIEW"
  }
}
```

### GET /decisions/{scan_session_id}

Retrieve a previously made decision.

**Response 200**

```json
{
  "scan_session_id": "sess_abc123",
  "decision_result": "VERIFIED",
  "decision_reason": "ALL_REGIONS_STRONG_MATCH",
  "summary": {
    "required_region_count": 3,
    "completed_region_count": 3,
    "missing_regions": [],
    "all_required_regions_satisfied": true,
    "result_reason": "ALL_REGIONS_STRONG_MATCH"
  },
  "created_at": "2026-04-24T10:20:00Z"
}
```

### GET /health

Returns `{"status": "ok"}` when the process is alive.

### GET /ready

Returns 200 when the service can reach the database and SQS.

## Decision Logic

The decision engine evaluates the following rules in order. The first matching rule determines the outcome:

| Priority | Result | Reason | Condition |
|---|---|---|---|
| 1 | *(existing decision)* | -- | If a decision already exists for this session, return it (idempotent). |
| 2 | `INCONCLUSIVE` | `MISSING_REQUIRED_REGIONS` | Any required region has not been scored. |
| 3 | `INCONCLUSIVE` | `NO_REGION_SCORES` | No region scores exist at all. |
| 4 | `UNVERIFIED` | `REGION_MISMATCH_DETECTED` | Any region has a `MISMATCH` decision. |
| 5 | `UNVERIFIED` | `COUNTERFEIT_SIMILARITY_EXCEEDS_AUTHENTIC` | Any region's counterfeit score exceeds its authentic score. |
| 6 | `VERIFIED` | `ALL_REGIONS_STRONG_MATCH` | All regions are `STRONG_MATCH`, average authentic score >= 0.85, and average counterfeit score < 0.40. |
| 7 | `EXPERT_REVIEW_REQUIRED` | `MODERATE_MATCH_REQUIRES_REVIEW` | Average authentic score >= 0.60. |
| 8 | `INCONCLUSIVE` | `INSUFFICIENT_SIMILARITY` | None of the above conditions are met. |

## Decision Summary

Every decision includes a summary object:

| Field | Description |
|---|---|
| `required_region_count` | Total number of regions required by the scan recipe. |
| `completed_region_count` | Number of regions that have been scored. |
| `missing_regions` | List of region codes that have not been scored. |
| `all_required_regions_satisfied` | Boolean indicating all required regions are present. |
| `result_reason` | Machine-readable reason code matching the decision reason. |

## Worker Behavior

The worker consumes `REGION_SCORED` events from the `decision-queue`. On each event it:

1. Checks if a decision already exists for the scan session (if so, skips).
2. Checks if all required regions have been scored (if not, skips and waits for more events).
3. Runs the decision engine and persists the result.
4. Updates `scan_sessions.status` to match the decision result.

## Events Consumed

| Event | Queue | Description |
|---|---|---|
| `REGION_SCORED` | `decision-queue` | Triggers a decision check. The worker evaluates whether all regions are ready. |

## Events Published

This service does not publish events to other queues. It is the terminal pipeline stage.

## Audit Events

| Event | Description |
|---|---|
| `DECISION_CREATED` | Recorded when a new authentication decision is persisted. |

## Database Tables

| Table | Access | Purpose |
|---|---|---|
| `authentication_decisions` | Read/Write | Persist and retrieve final decisions. |
| `scan_sessions` | Read/Write | Read session metadata; update `status` after decision. |
| `scan_recipe_regions` | Read | Determine which regions are required for the scan recipe. |
| `region_scores` | Read | Retrieve all scored regions for the session. |
| `processing_runs` | Read/Write | Idempotency tracking. |

## S3 Usage

This service does not access S3.

## Configuration

| Setting | Description |
|---|---|
| `sqs_decision_queue` | SQS queue URL for incoming decision trigger events. |

## Constants

| Constant | Value |
|---|---|
| `DECISION_RULE_VERSION` | `decision_rules_v0.2.0` |
| `EMBEDDING_MODEL_VERSION` | `stub_embedder_v0.1.0` |
| `REFERENCE_DATASET_VERSION` | `seed_v0.1.0` |

## Local Development

```bash
cd services/decision-service

pip install -e ".[dev]"

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8301 --reload

# Run the worker
python -m app.worker
```

Requires PostgreSQL and LocalStack (or real AWS) for SQS. Requires seeded scan recipes and region scores to produce meaningful decisions.

## Observability

- Structured logs include `scan_session_id`, `decision_result`, `decision_reason`, and the full summary.
- Audit event `DECISION_CREATED` is recorded for every new decision.
- Skipped decision attempts (existing decision or incomplete regions) are logged at DEBUG level.

## Idempotency

Key format: `{scan_session_id}|DECISION|decision_rules_v0.2.0`

The decision engine is inherently idempotent: if a decision already exists for a session, the existing decision is returned without recomputation. The `processing_runs` table provides an additional layer of protection against concurrent processing.

## Security Notes

- The decision result directly affects whether an item is certified as authentic. The rule engine is deterministic and auditable.
- No image data or embedding vectors flow through this service; only aggregate scores and identifiers.
- The `scan_sessions.status` update is the only write to a table owned by another service. This cross-service write is intentional to keep the session status in sync.

## Current Limitations

- Decision thresholds (0.85, 0.60, 0.40, etc.) are hardcoded. There is no per-brand or per-item-type configuration.
- `decision_rules_v0.2.0` indicates these rules have been revised once from v0.1.0. The version is tracked for auditability.
- No weighting of regions by importance. All required regions contribute equally.
- The `EXPERT_REVIEW_REQUIRED` outcome requires manual handling via the review-service; there is no automated escalation.

## Related Documentation

- [Region Scoring Service](../region-scoring-service/README.md) -- preceding pipeline stage.
- [Scan Recipe Service](../scan-recipe-service/README.md) -- defines required regions per item type.
- [Review Service](../review-service/README.md) -- handles expert review workflows for `EXPERT_REVIEW_REQUIRED` outcomes.
- [Certificate Service](../certificate-service/README.md) -- generates certificates for `VERIFIED` decisions.
