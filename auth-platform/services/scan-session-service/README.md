# scan-session-service

Manages authentication scan sessions. Creates sessions, resolves scan recipes via the scan-recipe-service, and tracks session lifecycle.

## Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `POST /scan-sessions` - Create a new scan session
- `GET /scan-sessions/{scan_session_id}` - Get session by ID

## Port

8101
