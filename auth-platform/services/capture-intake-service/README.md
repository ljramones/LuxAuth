# Capture Intake Service

## Purpose

Device-agnostic capture session management service. Manages capture protocols (which define required regions for a capture workflow), capture sessions (which track a device's image capture progress), and image uploads. Provides region completeness tracking so callers know when all required images have been captured.

## Responsibilities

- Create and serve capture protocols with region definitions
- Create capture sessions linked to a protocol and device
- Accept image uploads with region code validation against the protocol
- Track per-region image completeness (uploaded vs. required counts)
- Manage session lifecycle: CREATED -> CAPTURING -> COMPLETE/INCOMPLETE
- Upload raw images to S3 (auth-platform-raw-evidence bucket)
- Publish IMAGE_UPLOADED events to the image-quality-queue (SQS)
- Record audit events for all write operations

## Non-Responsibilities

- Does not control microscope hardware
- Does not run image quality analysis (image-quality-service consumes the queue)
- Does not normalize images or generate embeddings
- Does not make authentication decisions
- Does not manage scan sessions (scan-session-service handles those)

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | capture-intake-service |
| Port | 8106 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### GET /health

Health check endpoint.

### GET /ready

Readiness check endpoint.

### GET /capture-protocols

List all active capture protocols.

**Response (200):** Array of protocol objects (status = 'active', ordered by protocol_code).

### GET /capture-protocols/{protocol_code}

Retrieve a capture protocol by code, including its region definitions.

**Response (200):**
```json
{
  "id": "uuid",
  "protocol_code": "lv_monogram_handbag_v1",
  "protocol_version": "v0.1.0",
  "brand": "Louis Vuitton",
  "category": "handbag",
  "material": "monogram_canvas",
  "description": "...",
  "regions": [
    {"region_code": "EXTERIOR_CANVAS", "display_name": "Exterior Canvas Pattern", "min_images": 1, "sort_order": 0}
  ]
}
```

**Failures:** 404 if protocol not found.

### POST /capture-protocols

Create a new capture protocol with region definitions.

**Request:**
```json
{
  "protocol_code": "lv_monogram_handbag_v1",
  "protocol_version": "v0.1.0",
  "brand": "Louis Vuitton",
  "category": "handbag",
  "material": "monogram_canvas",
  "description": "Protocol for LV monogram canvas handbags",
  "regions": [
    {"region_code": "EXTERIOR_CANVAS", "display_name": "Exterior Canvas Pattern", "min_images": 1},
    {"region_code": "FRONT_LOGO_PRINT", "display_name": "Front Logo Print", "min_images": 2}
  ]
}
```

**Response (201):** Returns protocol ID and protocol_code.

### POST /capture-sessions

Create a new capture session linked to a protocol and device.

**Request:**
```json
{
  "device_id": "uuid-string",
  "calibration_id": "uuid-string-or-null",
  "capture_protocol_code": "lv_monogram_handbag_v1",
  "source_type": "api",
  "operator": "operator-name",
  "notes": "optional notes"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "status": "CREATED",
  "capture_protocol_code": "lv_monogram_handbag_v1"
}
```

**Failures:** 400 if protocol_code not found or not active.

### GET /capture-sessions/{capture_session_id}

Retrieve a capture session by UUID.

**Failures:** 404 if session not found.

### GET /capture-sessions/{capture_session_id}/status

Get detailed capture progress including per-region completeness.

**Response (200):**
```json
{
  "capture_session_id": "uuid",
  "status": "CAPTURING",
  "protocol_code": "lv_monogram_handbag_v1",
  "all_regions_satisfied": false,
  "total_images": 3,
  "missing_regions": ["FRONT_LOGO_PRINT"],
  "region_status": [
    {"region_code": "EXTERIOR_CANVAS", "required": 1, "uploaded": 2, "satisfied": true},
    {"region_code": "FRONT_LOGO_PRINT", "required": 2, "uploaded": 0, "satisfied": false}
  ]
}
```

### POST /capture-sessions/{capture_session_id}/images

Upload an image for a capture session region.

**Content-Type:** multipart/form-data

**Form fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| file | UploadFile | Yes | The image file |
| region_code | string | Yes | Region code from the capture protocol |
| external_item_id | string | No | Item identifier (default: "default_item") |
| capture_index | int | No | Capture sequence index (default: 0) |
| magnification_profile | string | No | Magnification setting used |
| lighting_profile | string | No | Lighting setting used |
| authenticity_status | string | No | Known label for training data |
| label_confidence | string | No | Confidence of the label |
| provenance_type | string | No | Provenance classification |
| notes | string | No | Free-form notes |

**Response (201):**
```json
{
  "id": "uuid",
  "capture_session_id": "uuid",
  "region_code": "EXTERIOR_CANVAS",
  "raw_object_uri": "s3://auth-platform-raw-evidence/captures/{session}/{item}/raw/{id}.jpg",
  "width": 1920,
  "height": 1080,
  "sha256_checksum": "hex-string"
}
```

**Failures:**
- 404 if capture session not found
- 400 if region_code is not valid for the session's protocol
- 400 if the uploaded file is not a valid image

### POST /capture-sessions/{capture_session_id}/complete

Mark a capture session as complete. Checks region completeness and sets status to COMPLETE (all regions satisfied) or INCOMPLETE (missing regions).

**Response (200):**
```json
{
  "capture_session_id": "uuid",
  "status": "COMPLETE",
  "all_regions_satisfied": true,
  "total_images": 5,
  "missing_regions": [],
  "region_status": [
    {"region_code": "EXTERIOR_CANVAS", "required": 1, "uploaded": 2, "satisfied": true}
  ]
}
```

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
  "image_id": "uuid",
  "source_service": "capture-intake-service",
  "payload": {
    "capture_session_id": "uuid",
    "region_code": "EXTERIOR_CANVAS",
    "raw_object_uri": "s3://...",
    "external_item_id": "default_item",
    "source": "capture_intake"
  }
}
```

If the queue is unreachable, the upload still succeeds (warning logged). The event is not retried.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| capture_protocols | Read/Write | Protocol definitions |
| capture_protocol_regions | Read/Write | Region requirements per protocol |
| capture_sessions | Read/Write | Session lifecycle and status |
| capture_session_images | Read/Write | Image metadata per session |

## S3 / Object Storage Usage

| Bucket | Key Pattern | Purpose |
|---|---|---|
| auth-platform-raw-evidence | `captures/{capture_session_id}/items/{external_item_id}/raw/{image_id}.{ext}` | Raw capture images |

Extension is derived from detected image format (JPEG->jpg, PNG->png, etc.).

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | capture-intake-service |
| PORT | Listen port | 8106 |
| LOG_LEVEL | Logging level | DEBUG |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| AWS_ENDPOINT_URL | LocalStack/S3 endpoint | http://localstack:4566 |
| AWS_ACCESS_KEY_ID | AWS access key | test |
| AWS_SECRET_ACCESS_KEY | AWS secret key | test |
| AWS_DEFAULT_REGION | AWS region | us-east-1 |
| raw_evidence_bucket | S3 bucket for raw images | auth-platform-raw-evidence |
| image_quality_queue | SQS queue name for image events | image-quality-queue |

## Local Development

```bash
docker compose logs -f capture-intake-service
curl -s http://localhost:8106/health | jq .

# List protocols
curl -s http://localhost:8106/capture-protocols | jq .

# Create a session
curl -X POST http://localhost:8106/capture-sessions \
  -H "Content-Type: application/json" \
  -d '{"device_id": "dev-001", "capture_protocol_code": "lv_monogram_handbag_v1"}'

# Upload an image
curl -X POST http://localhost:8106/capture-sessions/{session_id}/images \
  -F "file=@test_image.jpg" \
  -F "region_code=EXTERIOR_CANVAS"

# Check completeness
curl -s http://localhost:8106/capture-sessions/{session_id}/status | jq .

# Complete session
curl -X POST http://localhost:8106/capture-sessions/{session_id}/complete | jq .
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- Audit events: CAPTURE_PROTOCOL_CREATED, CAPTURE_SESSION_CREATED, CAPTURE_SESSION_IMAGE_UPLOADED, CAPTURE_SESSION_COMPLETED, CAPTURE_SESSION_INCOMPLETE

## Idempotency and Failure Handling

- No idempotency keys — each POST creates a new record
- If SQS publish fails, the image is still stored in S3 and the database (warning logged)
- Session status update to CAPTURING is conditional (only if current status is CREATED)
- Complete endpoint can be called multiple times (re-evaluates region completeness each time)

## Security Notes

- Validates all uploaded files as real images (decodes with Pillow via auth_common.imaging.validate_image)
- Rejects non-image files and corrupt images with 400
- Validates region codes against the capture protocol — rejects arbitrary region codes
- Does not accept images for unknown capture sessions

## Current Limitations

- No maximum file size enforcement at the application level
- No rate limiting on uploads
- SQS event publish is fire-and-forget (no retry, no dead-letter queue handling)
- No duplicate image detection
- Protocol code uniqueness is not enforced at the application level
- No protocol deactivation endpoint
- Session complete/incomplete status can be overwritten by calling complete again

## Related Documentation

- [Event Flow](../../docs/architecture/event-flow.md)
- [Service Boundaries](../../docs/architecture/service-boundaries.md)
