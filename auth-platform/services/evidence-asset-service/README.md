# Evidence Asset Service

## Purpose

Handles raw image intake for authentication scan sessions. Receives microscope capture images via multipart upload, validates them, stores them in S3, records metadata in PostgreSQL, and publishes events to trigger downstream image quality processing.

## Responsibilities

- Accept image uploads linked to scan sessions and region codes
- Validate uploaded images using auth_common.imaging.validate_image (format detection, dimension extraction, decode verification)
- Compute SHA-256 and MD5 checksums for integrity verification
- Upload raw images to S3 (auth-platform-raw-evidence bucket)
- Store image asset metadata in PostgreSQL
- Validate region codes against the scan recipe assigned to the session
- Update scan session status from CREATED to CAPTURING on first image upload
- Publish IMAGE_UPLOADED events to the image-quality-queue (SQS)
- Record IMAGE_UPLOADED audit events

## Non-Responsibilities

- Does not create or manage scan sessions (scan-session-service does that)
- Does not run image quality analysis (image-quality-service consumes the queue)
- Does not normalize or generate embeddings
- Does not make authentication decisions
- Does not control microscope hardware

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | evidence-asset-service |
| Port | 8104 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### POST /scan-sessions/{scan_session_id}/images

Upload a raw microscope image for a scan session region.

**Content-Type:** multipart/form-data

**Form fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| file | UploadFile | Yes | The image file (JPEG, PNG, TIFF, BMP, WEBP) |
| region_code | string | Yes | Region code from the scan recipe (e.g. EXTERIOR_CANVAS) |
| device_id | UUID | Yes | Capture device identifier |

**Response (201):**
```json
{
  "id": "uuid",
  "scan_session_id": "uuid",
  "region_code": "EXTERIOR_CANVAS",
  "raw_object_uri": "s3://auth-platform-raw-evidence/scans/{org_id}/{scan_session_id}/raw/{image_id}.jpg",
  "checksum": "md5-hex-string",
  "file_size_bytes": 245760,
  "created_at": "2026-04-25T..."
}
```

**Failures:**
- 404 if scan session not found
- 400 if region_code is not valid for the session's scan recipe
- 400 if the uploaded file is not a valid image (corrupt, undecodable, or non-image format)

### GET /scan-sessions/{scan_session_id}/images

List all uploaded images for a scan session, ordered by creation time.

**Response (200):** Array of image asset objects.

## Events Consumed

This service does not consume SQS events.

## Events Published

| Event | Queue | Trigger |
|---|---|---|
| IMAGE_UPLOADED | image-quality-queue | After successful image upload and S3 storage |

**IMAGE_UPLOADED payload:**
```json
{
  "event_type": "IMAGE_UPLOADED",
  "correlation_id": "...",
  "scan_session_id": "uuid",
  "image_id": "uuid",
  "payload": {
    "region_code": "EXTERIOR_CANVAS",
    "raw_object_uri": "s3://auth-platform-raw-evidence/scans/.../raw/image.jpg",
    "checksum": "md5-hex",
    "sha256_checksum": "sha256-hex",
    "file_size_bytes": 245760
  }
}
```

If the queue is unreachable, the upload still succeeds (warning logged). The event is not retried.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| scan_sessions | Read | Validate session exists, get organization_id, read/update status |
| scan_recipe_regions | Read | Validate region_code against the session's scan recipe |
| image_assets | Write | Store image metadata (checksums, dimensions, S3 URI, format) |

## S3 / Object Storage Usage

| Bucket | Key Pattern | Purpose |
|---|---|---|
| auth-platform-raw-evidence | `scans/{org_id}/{scan_session_id}/raw/{image_id}.{ext}` | Raw microscope capture images |

Extension is derived from detected image format (JPEG->jpg, PNG->png, TIFF->tiff, BMP->bmp, WEBP->webp).

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | evidence-asset-service |
| PORT | Listen port | 8104 |
| LOG_LEVEL | Logging level | DEBUG |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| AWS_ENDPOINT_URL | LocalStack/S3 endpoint | http://localstack:4566 |
| raw_evidence_bucket | S3 bucket for raw images | auth-platform-raw-evidence |
| image_upload_queue | SQS queue name for image events | image-quality-queue |

## Local Development

```bash
docker compose logs -f evidence-asset-service
curl -s http://localhost:8104/health | jq .

# Upload a test image
curl -X POST http://localhost:8104/scan-sessions/{session_id}/images \
  -F "file=@test_image.jpg" \
  -F "region_code=EXTERIOR_CANVAS" \
  -F "device_id=00000000-0000-0000-0000-000000000001"
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- Audit events: IMAGE_UPLOADED
- Logs image_id and scan_session_id on each upload

## Idempotency and Failure Handling

- No idempotency key — each POST creates a new image asset record
- If SQS publish fails, the image is still stored in S3 and the database (warning logged)
- Session status update to CAPTURING is conditional (only if current status is CREATED)

## Security Notes

- Validates all uploaded files as real images (decodes with Pillow via auth_common.imaging.validate_image)
- Rejects non-image files and corrupt images with 400
- Validates region codes against the scan recipe — rejects arbitrary region codes
- Computes SHA-256 and MD5 checksums for tamper detection

## Current Limitations

- No maximum file size enforcement at the application level
- No rate limiting on uploads
- SQS event publish is fire-and-forget (no retry, no dead-letter queue handling)
- No duplicate image detection (same file can be uploaded multiple times)

## Related Documentation

- [Event Flow](../../docs/architecture/event-flow.md)
- [Service Boundaries](../../docs/architecture/service-boundaries.md)
