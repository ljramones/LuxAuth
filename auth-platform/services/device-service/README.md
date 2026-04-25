# device-service

Manages device registration and lookup for authentication scanning devices.

## Endpoints

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `POST /devices/register` - Register a new device
- `GET /devices/{device_id}` - Get device by ID

## Port

8103
