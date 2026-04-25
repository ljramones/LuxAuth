# Embedding Service

Generates 768-dimensional vector embeddings from normalized evidence images and stores them via pgvector.

## Endpoints

| Method | Path                          | Description                    |
|--------|-------------------------------|--------------------------------|
| GET    | /health                       | Liveness probe                 |
| GET    | /ready                        | Readiness probe                |
| POST   | /process/{image_asset_id}     | Generate embedding             |
| GET    | /embeddings/{image_asset_id}  | Retrieve embedding metadata    |

## Configuration

| Variable              | Default                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| EMB_DATABASE_URL      | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| EMB_PORT              | 8203                                                                    |
| EMB_LOG_LEVEL         | INFO                                                                    |

## Running locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8203
```
