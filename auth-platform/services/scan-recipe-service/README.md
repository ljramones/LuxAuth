# Scan Recipe Service

## Purpose

Manages scan recipes that define which microscope capture regions are required for authenticating a specific brand/category/material combination. Recipes are the protocol contract between the capture client and the authentication pipeline.

## Responsibilities

- Store and serve scan recipe definitions
- Resolve the best matching recipe for a brand/category/material query
- Return region requirements (region codes, minimum images, magnification, lighting)

## Non-Responsibilities

- Does not create scan sessions
- Does not validate or store images
- Does not make authentication decisions
- Does not manage capture protocols (capture-intake-service has separate protocols)

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | scan-recipe-service |
| Port | 8102 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### GET /scan-recipes/resolve?brand=&category=&material=

Resolve the best active recipe for the given parameters. Returns the highest-version active recipe.

**Response (200):**
```json
{
  "id": "uuid",
  "recipe_key": "lv_monogram_canvas_handbag_v1",
  "brand": "Louis Vuitton",
  "category": "handbag",
  "material": "monogram_canvas",
  "version": 1,
  "regions": [
    {"region_code": "EXTERIOR_CANVAS", "display_name": "Exterior Canvas Pattern", "min_images": 1, "magnification_profile": "10x", "lighting_profile": "DIFFUSE"}
  ]
}
```

**Failures:**
- 404 if no active recipe matches

### GET /scan-recipes/{recipe_id}

Fetch a specific recipe by UUID.

**Failures:**
- 404 if recipe not found

## Events Consumed

This service does not consume SQS events.

## Events Published

This service does not publish SQS events.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| scan_recipes | Read | Recipe definitions |
| scan_recipe_regions | Read | Region requirements per recipe |

## S3 / Object Storage Usage

This service does not directly use object storage.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | scan-recipe-service |
| SERVICE_PORT | Listen port | 8102 |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |

## Local Development

```bash
docker compose logs -f scan-recipe-service
curl -s "http://localhost:8102/scan-recipes/resolve?brand=Louis+Vuitton&category=handbag&material=monogram_canvas" | jq .
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- No audit events currently recorded

## Idempotency and Failure Handling

- Read-only service — no idempotency concerns
- Returns 404 if no matching recipe exists

## Security Notes

- Serves only active recipes (is_active = true)
- No write endpoints in current implementation (recipes are seeded via SQL)

## Current Limitations

- Recipes are seeded in the database init SQL, not created via API
- No recipe versioning management API
- No recipe creation/update endpoints

## Related Documentation

- [Service Boundaries](../../docs/architecture/service-boundaries.md)
