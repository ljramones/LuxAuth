# Certificate Service

Issues and verifies authentication certificates for verified luxury goods.

## Port
8303

## Endpoints
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `POST /certificates` - Issue a certificate for a verified scan session
- `GET /certificates/{certificate_id}` - Get certificate by ID
- `GET /certificates/verify/{certificate_number}` - Public verification endpoint
