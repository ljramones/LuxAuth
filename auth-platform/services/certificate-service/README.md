# Certificate Service

## Purpose

Issues authentication certificates for verified scan sessions. Provides public verification of certificate numbers.

## Responsibilities

- Issue certificates for VERIFIED scan sessions only
- Generate unique certificate numbers (CERT-{uuid[:8]})
- Provide certificate lookup by ID and by certificate number

## Non-Responsibilities

- Does not make authentication decisions
- Does not verify certificate cryptographic integrity (planned)
- Does not manage certificate expiration
- Does not send certificates to customers

## Runtime

| Property | Value |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Docker service | certificate-service |
| Port | 8303 |
| Health | `GET /health` |
| Readiness | `GET /ready` |

## Main APIs

### POST /certificates

Issue a certificate for a verified scan session.

**Request:**
```json
{
  "scan_session_id": "uuid"
}
```

**Response (201):** Certificate with certificate_number.

**Failures:**
- 400 if the scan session's authentication decision is not VERIFIED

### GET /certificates/{certificate_id}

Retrieve certificate by UUID.

### GET /certificates/verify/{certificate_number}

Public verification endpoint — look up certificate by number.

## Events Consumed

This service does not consume SQS events.

## Events Published

This service does not publish SQS events.

## Database Tables Used

| Table | Access | Purpose |
|---|---|---|
| authentication_decisions | Read | Verify decision is VERIFIED before issuing |
| certificates | Read/Write | Certificate records |

## S3 / Object Storage Usage

This service does not directly use object storage.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| SERVICE_NAME | Service identifier | certificate-service |
| SERVICE_PORT | Listen port | 8303 |
| DATABASE_URL | PostgreSQL connection | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |

## Local Development

```bash
docker compose logs -f certificate-service
curl -s http://localhost:8303/health | jq .
```

## Observability

- Structured JSON logs via structlog
- Correlation ID propagated from HTTP headers
- No audit events currently recorded (planned)

## Idempotency and Failure Handling

- Certificate number uniqueness enforced by DB UNIQUE constraint
- No idempotency keys

## Security Notes

- Only issues certificates for VERIFIED decisions
- Certificate numbers are UUID-based, not sequential

## Current Limitations

- Skeleton implementation
- No certificate expiration management
- No hosted certificate verification page
- No audit events recorded
- No anti-forgery measures beyond unique certificate numbers

## Related Documentation

- [Service Boundaries](../../docs/architecture/service-boundaries.md)
