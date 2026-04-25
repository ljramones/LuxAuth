# Region Scoring Service

Scores individual image regions against reference embeddings and publishes results to the decision queue.

## Port
8205

## Endpoints
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `POST /score` - Score a region
- `GET /scores/{scan_session_id}` - Get all scores for a scan session

## Events Published
- `REGION_SCORED` -> `decision-queue`
