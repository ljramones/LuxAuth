# Vector Search Service

Performs cosine-similarity search against reference embeddings to find authentic and counterfeit matches.

## Endpoints

| Method | Path                        | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | /health                     | Liveness probe                     |
| GET    | /ready                      | Readiness probe                    |
| POST   | /search/{image_asset_id}    | Run similarity search              |
| GET    | /results/{image_asset_id}   | Retrieve cached search result      |

## Configuration

| Variable             | Default                                                                 |
|----------------------|-------------------------------------------------------------------------|
| VS_DATABASE_URL      | postgresql+asyncpg://authplatform:authplatform@postgres:5432/authplatform |
| VS_PORT              | 8204                                                                    |
| VS_LOG_LEVEL         | INFO                                                                    |
| VS_TOP_K             | 5                                                                       |

## Running locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8204
```
