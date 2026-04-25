# Device Service

## Purpose

Manages capture device registration and calibration profiles. Provides a registry of known microscopes and their calibration state for the authentication pipeline.

## Responsibilities

- Register capture devices with serial number, type, and firmware version
- Create and retrieve device calibration profiles
- Record DEVICE_REGISTERED and DEVICE_CALIBRATION_CREATED audit events

## Non-Responsibilities

- Does not control microscope hardware
- Does not capture or store images
- Does not validate image quality
- Does not manage capture sessions or protocols

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | device-service |
| Port | 8103 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### POST /devices/register

Register a new capture device.

**Request:**
```json
{
  "device_serial": "DINO-LITE-AM7115MZT-001",
  "device_type": "HANDHELD_MICROSCOPE",
  "organization_id": "uuid",
  "firmware_version": "2.4.1"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "device_serial": "DINO-LITE-AM7115MZT-001",
  "device_type": "HANDHELD_MICROSCOPE",
  "status": "active",
  "firmware_version": "2.4.1",
  "created_at": "2026-04-25T..."
}
```

### GET /devices/{device_id}

Retrieve device by UUID.

### POST /devices/{device_id}/calibrations

Create a calibration profile for a device.

**Request:** Flexible JSON body with calibration_profile object.

**Response (201):** Returns calibration ID, device ID, calibrated_at, status.

**Failures:** 404 if device not found.

### GET /devices/{device_id}/calibrations/{calibration_id}

Retrieve a specific calibration profile.

## Events Consumed

This service does not consume SQS events.

## Events Published

This service does not publish SQS events.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| devices | Read/Write | Device registration |
| device_calibrations | Read/Write | Calibration profiles |

## S3 / Object Storage Usage

This service does not directly use object storage.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | device-service |
| SERVICE_PORT | Listen port | 8103 |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |

## Local Development

```bash
docker compose logs -f device-service
curl -s http://localhost:8103/health | jq .
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- Audit events: DEVICE_REGISTERED, DEVICE_CALIBRATION_CREATED

## Idempotency and Failure Handling

- No idempotency key — each POST creates a new record
- Device serial uniqueness is not enforced at application level (DB index exists)

## Security Notes

- Accepts any device_type and firmware_version
- Calibration profiles stored as JSONB — flexible schema

## Current Limitations

- No device deactivation endpoint
- No calibration expiry enforcement
- Calibration expires_at is hardcoded to 2027-01-01

## Related Documentation

- [Microscope Acceptance Runbook](../../../docs/operations/microscope-acceptance-runbook.md)
- [Capture Quality Guide](../../../docs/operations/capture-quality-guide.md)
