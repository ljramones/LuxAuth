# Image Quality Service

Assesses uploaded evidence images for sharpness, exposure, and glare before they proceed through the authentication pipeline.

## Endpoints

| Method | Path                        | Description                      |
|--------|-----------------------------|----------------------------------|
| GET    | /health                     | Liveness probe                   |
| GET    | /ready                      | Readiness probe                  |
| POST   | /process/{image_asset_id}   | Run quality assessment           |
| GET    | /reports/{image_asset_id}   | Retrieve a stored quality report |

## Configuration

| Variable            | Default                                                                 |
|---------------------|-------------------------------------------------------------------------|
| IQS_DATABASE_URL    | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| IQS_PORT            | 8201                                                                    |
| IQS_LOG_LEVEL       | INFO                                                                    |

## Running locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8201
```
