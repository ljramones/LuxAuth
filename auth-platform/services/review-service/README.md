# Review Service

## Purpose

Manages the human expert review queue for authentication decisions that require manual inspection. Allows creating review cases and recording reviewer decisions.

## Responsibilities

- List and retrieve review cases
- Create review cases linked to scan sessions and authentication decisions
- Record reviewer decisions with notes

## Non-Responsibilities

- Does not make automated authentication decisions
- Does not process images or embeddings
- Does not issue certificates
- Does not send notifications to reviewers

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | review-service |
| Port | 8302 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### GET /review-cases

List review cases with pagination.

**Query params:** limit (default 50), offset (default 0)

### GET /review-cases/{review_case_id}

Retrieve a single review case.

### POST /review-cases

Create a new review case.

**Request:**
```json
{
  "scan_session_id": "uuid",
  "authentication_decision_id": "uuid"
}
```

### POST /review-cases/{review_case_id}/decision

Submit a reviewer's decision.

**Request:**
```json
{
  "reviewer_decision": "VERIFIED",
  "reviewer_notes": "Manual inspection confirms authentic stitching pattern.",
  "reviewer_id": "reviewer-uuid"
}
```

## Events Consumed

This service does not consume SQS events.

## Events Published

This service does not publish SQS events.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| review_cases | Read/Write | Review case lifecycle |

## S3 / Object Storage Usage

This service does not directly use object storage.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | review-service |
| SERVICE_PORT | Listen port | 8302 |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |

## Local Development

```bash
docker compose logs -f review-service
curl -s http://localhost:8302/review-cases | jq .
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- No audit events currently recorded (planned)

## Idempotency and Failure Handling

- No idempotency keys
- Review decisions can be submitted once per case (status moves to COMPLETED)

## Security Notes

- No authentication/authorization on reviewer identity
- reviewer_id is a free-form string

## Current Limitations

- Skeleton implementation — no review UI
- No notification when review cases are created
- No audit events recorded
- No filtering by status on list endpoint

## Related Documentation

- [Service Boundaries](../../docs/architecture/service-boundaries.md)
