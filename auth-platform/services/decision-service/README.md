# Decision Service

Aggregates region scores and produces authentication decisions (VERIFIED, UNVERIFIED, EXPERT_REVIEW_REQUIRED, INCONCLUSIVE).

## Port
8301

## Endpoints
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `POST /decide/{scan_session_id}` - Make authentication decision
- `GET /decisions/{scan_session_id}` - Get decision for a scan session
