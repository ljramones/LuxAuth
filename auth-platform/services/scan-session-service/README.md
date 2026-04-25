# Scan Session Service

## Purpose

Manages authentication scan sessions. Creates sessions with recipe resolution, tracks session status through the authentication lifecycle, and links sessions to scan recipes and required regions.

## Responsibilities

- Create scan sessions with claimed brand/category/material
- Resolve scan recipe by calling scan-recipe-service
- Store scan session records in PostgreSQL
- Return required region list from resolved recipe
- Track session status transitions (CREATED → CAPTURING → VERIFIED/UNVERIFIED/INCONCLUSIVE/EXPERT_REVIEW_REQUIRED)
- Record SCAN_CREATED audit events

## Non-Responsibilities

- Does not receive or store images (evidence-asset-service does that)
- Does not run image quality, normalization, or embedding pipelines
- Does not make authentication decisions (decision-service does that)
- Does not control microscope hardware

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | scan-session-service |
| Port | 8101 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### POST /scan-sessions

Create a new authentication scan session.

**Request:**
```json
{
  "claimed_brand": "Louis Vuitton",
  "claimed_category": "handbag",
  "claimed_material": "monogram_canvas",
  "claimed_model": null,
  "device_id": "uuid",
  "organization_id": "uuid",
  "operator_id": null
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "status": "CREATED",
  "claimed_brand": "Louis Vuitton",
  "claimed_category": "handbag",
  "claimed_material": "monogram_canvas",
  "scan_recipe_id": "uuid",
  "required_regions": ["EXTERIOR_CANVAS", "FRONT_LOGO_PRINT"],
  "created_at": "2026-04-25T..."
}
```

**Failures:**
- 400 if no scan recipe matches the claimed brand/category/material

### GET /scan-sessions/{scan_session_id}

Retrieve a scan session with its required regions.

**Failures:**
- 404 if session not found

## Events Consumed

This service does not consume SQS events.

## Events Published

This service does not publish SQS events. It calls scan-recipe-service via HTTP.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| scan_sessions | Read/Write | Core session records |
| scan_recipe_regions | Read | Fetch required regions for a recipe |

## S3 / Object Storage Usage

This service does not directly use object storage.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | scan-session-service |
| SERVICE_PORT | Listen port | 8101 |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| AWS_ENDPOINT_URL | LocalStack URL | http://localstack:4566 |
| scan_recipe_service_url | Recipe service URL | http://scan-recipe-service:8102 |

## Local Development

```bash
docker compose logs -f scan-session-service
curl -s http://localhost:8101/health | jq .
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- Audit events: SCAN_CREATED

## Idempotency and Failure Handling

- No idempotency key — each POST creates a new session
- If scan-recipe-service is unreachable, returns 400

## Security Notes

- Validates claimed brand/category/material against active recipes
- Does not accept arbitrary recipe IDs from client

## Current Limitations

- Recipe resolution requires scan-recipe-service to be available
- No pagination on session listing (GET by ID only)
- Session status is updated by decision-service, not this service

## Related Documentation

- [Event Flow](../../docs/architecture/event-flow.md)
- [Service Boundaries](../../docs/architecture/service-boundaries.md)
