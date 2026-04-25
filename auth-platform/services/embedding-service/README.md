# Embedding Service

## Purpose

Generates vector embeddings from normalized evidence images and stores them in PostgreSQL via pgvector. Supports two embedding backends: a hand-crafted texture baseline and an optional PyTorch ResNet18 model. The resulting 128-dimensional vectors are used by the vector search service to find similar reference items.

## Responsibilities

- Download normalized images from S3.
- Generate a 128-dimensional embedding vector using the configured backend.
- Store the embedding in the `embeddings` table using pgvector (`cast(:embedding as vector)`).
- Publish an event to advance the image to the vector search stage.

## Non-Responsibilities

- Does not normalize images (see normalization-service).
- Does not perform similarity search (see vector-search-service).
- Does not train models; it only runs inference with existing model artifacts.

## Runtime

| Property | Value |
|---|---|
| Port | `8203` |
| Healthcheck | `GET /health` |
| Readiness | `GET /ready` |
| Worker queue | `embedding-queue` |
| Framework | FastAPI |

## Main APIs

### POST /process/{image_asset_id}

Generate an embedding for a single normalized image.

**Request**

```
POST /process/01J7X9K2M3N4P5Q6R7S8T9U0
```

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "embedding_id": "emb_01JABC123",
  "embedding_model_version": "texture_baseline_v0.1.0",
  "dimensions": 128
}
```

### GET /embeddings/{image_asset_id}

Retrieve embedding metadata for a previously processed image.

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "embedding_id": "emb_01JABC123",
  "embedding_model_version": "texture_baseline_v0.1.0",
  "dimensions": 128,
  "created_at": "2026-04-24T10:17:00Z"
}
```

### GET /health

Returns `{"status": "ok"}` when the process is alive.

### GET /ready

Returns 200 when the service can reach the database and SQS.

## Embedding Backends

### texture_baseline_v0.1.0

Hand-crafted 128-dimensional feature vector computed from:

- **Grayscale histogram** -- intensity distribution features.
- **Color histograms** -- per-channel (R, G, B) distribution features.
- **Gradient histogram** -- edge orientation features from Sobel filters.
- **Local variance** -- texture roughness features from local pixel variance.

This is the default backend and requires no additional dependencies beyond NumPy/OpenCV.

### learned_metric_v0.1.0

PyTorch ResNet18 model loaded from S3 (`auth-platform-ml-artifacts` bucket). Produces a 128-dimensional embedding from the penultimate layer.

- Requires `torch` to be installed.
- If `torch` is not available at runtime, the service falls back to `texture_baseline_v0.1.0` with a warning log.
- Model weights are downloaded from S3 on first use and cached in memory.

## Events Consumed

| Event | Queue | Description |
|---|---|---|
| `IMAGE_NORMALIZED` | `embedding-queue` | Triggers embedding generation for a newly normalized image. |

## Events Published

| Event | Queue | Description |
|---|---|---|
| `EMBEDDING_GENERATED` | `vector-search-queue` | Published after the embedding is stored in pgvector. |

## Database Tables

| Table | Access | Purpose |
|---|---|---|
| `normalized_images` | Read | Look up the normalized image S3 key. |
| `embeddings` | Write | Store the 128-dim vector via pgvector. |
| `image_assets` | Read | Look up image metadata. |
| `model_versions` | Read | Look up model configuration and artifact paths. |
| `processing_runs` | Read/Write | Idempotency tracking. |

## S3 Usage

| Bucket | Access | Purpose |
|---|---|---|
| `auth-platform-normalized-evidence` | Read | Download the normalized PNG for embedding generation. |
| `auth-platform-ml-artifacts` | Read | Download PyTorch model weights (learned backend only). |

## Configuration

| Setting | Description |
|---|---|
| `embedding_model_version` | Which backend to use: `texture_baseline_v0.1.0` or `learned_metric_v0.1.0`. |
| `sqs_embedding_queue` | SQS queue URL for incoming embedding requests. |
| `sqs_vector_search_queue` | SQS queue URL for publishing embeddings downstream. |
| `s3_normalized_bucket` | S3 bucket for normalized images. |
| `s3_ml_artifacts_bucket` | S3 bucket for model artifacts. |

## Local Development

```bash
cd services/embedding-service

# Without PyTorch (texture baseline only)
pip install -e ".[dev]"

# With PyTorch support
pip install -e ".[dev,torch]"

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8203 --reload

# Run the worker
python -m app.worker
```

Requires PostgreSQL with the pgvector extension enabled, and LocalStack (or real AWS) for SQS and S3.

## Observability

- Structured logs include `image_asset_id`, `embedding_model_version`, and embedding dimensions.
- Logs a warning when falling back from `learned_metric` to `texture_baseline` due to missing torch.
- Audit event `EMBEDDING_GENERATED` is recorded for every successful embedding.

## Idempotency

Key format: `{image_id}|EMBEDDING|stub_embedder_v0.1.0`

Duplicate processing is prevented via the `processing_runs` table.

## Security Notes

- Model artifacts are loaded from a dedicated S3 bucket with read-only access.
- Embedding vectors are numeric arrays with no personally identifiable information, but they are derived from evidence images and should be treated as sensitive.
- S3 access uses IAM role credentials.

## Current Limitations

- All embeddings are 128-dimensional regardless of backend. Future model versions may use different dimensionalities.
- The `texture_baseline_v0.1.0` backend is deterministic but limited in discriminative power compared to learned models.
- PyTorch inference runs on CPU; no GPU scheduling is implemented.
- Model hot-swapping is not supported. Changing `embedding_model_version` requires a service restart.

## Related Documentation

- [Normalization Service](../normalization-service/README.md) -- preceding pipeline stage.
- [Vector Search Service](../vector-search-service/README.md) -- next pipeline stage after embedding generation.
