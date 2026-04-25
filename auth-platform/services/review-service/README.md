# Review Service

Manages expert review cases for authentication decisions requiring human review.

## Port
8302

## Endpoints
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /review-cases` - List review cases (paginated)
- `GET /review-cases/{review_case_id}` - Get single review case
- `POST /review-cases` - Create a review case
- `POST /review-cases/{review_case_id}/decision` - Submit reviewer decision
