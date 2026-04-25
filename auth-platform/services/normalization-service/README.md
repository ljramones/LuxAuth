# Normalization Service

Normalizes raw evidence images (color correction, resizing, etc.) before embedding generation.

## Endpoints

| Method | Path                        | Description                          |
|--------|-----------------------------|--------------------------------------|
| GET    | /health                     | Liveness probe                       |
| GET    | /ready                      | Readiness probe                      |
| POST   | /process/{image_asset_id}   | Normalize an image                   |
| GET    | /results/{image_asset_id}   | Retrieve normalization result        |

## Configuration

| Variable                | Default                                                                 |
|-------------------------|-------------------------------------------------------------------------|
| NORM_DATABASE_URL       | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| NORM_PORT               | 8202                                                                    |
| NORM_LOG_LEVEL          | INFO                                                                    |

## Running locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8202
```
