# evidence-asset-service

Handles image evidence uploads for scan sessions. Stores raw images in S3, records metadata in the database, and publishes IMAGE_UPLOADED events to SQS.

## Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `POST /scan-sessions/{scan_session_id}/images` - Upload an image (multipart form with file, region_code, device_id)
- `GET /scan-sessions/{scan_session_id}/images` - List images for a session

## Port

8104
