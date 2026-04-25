# Vector Search Service

## Purpose

Finds the nearest reference embeddings to a query image using pgvector cosine similarity. Splits results into authentic and counterfeit matches and computes cluster scores that downstream services use to make authentication decisions.

## Responsibilities

- Retrieve the query embedding from the `embeddings` table.
- Run cosine similarity search against `reference_embeddings` using pgvector.
- Filter results by region code, embedding model version, and dataset membership.
- Split results into `authentic_matches` and `counterfeit_matches` (top-k each).
- Compute `authentic_cluster_score`, `counterfeit_cluster_score`, and `ood_score`.
- Publish scores to the region scoring queue.

## Non-Responsibilities

- Does not generate embeddings (see embedding-service).
- Does not interpret similarity scores into authentication decisions (see region-scoring-service and decision-service).
- Does not manage reference datasets (see separate reference data tooling).

## Runtime

| Property | Value |
|---|---|
| Port | `8204` |
| Healthcheck | `GET /health` |
| Readiness | `GET /ready` |
| Worker queue | `vector-search-queue` |
| Framework | FastAPI |

## Main APIs

### POST /search/{image_asset_id}

Run similarity search for a single image embedding.

**Request**

```
POST /search/01J7X9K2M3N4P5Q6R7S8T9U0
```

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "authentic_matches": [
    {"reference_image_id": "ref_001", "similarity": 0.92},
    {"reference_image_id": "ref_002", "similarity": 0.88}
  ],
  "counterfeit_matches": [
    {"reference_image_id": "ref_101", "similarity": 0.35}
  ],
  "authentic_cluster_score": 0.90,
  "counterfeit_cluster_score": 0.35,
  "ood_score": 0.12
}
```

### GET /results/{image_asset_id}

Retrieve a previously computed search result.

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "authentic_cluster_score": 0.90,
  "counterfeit_cluster_score": 0.35,
  "ood_score": 0.12,
  "created_at": "2026-04-24T10:18:00Z"
}
```

### GET /health

Returns `{"status": "ok"}` when the process is alive.

### GET /ready

Returns 200 when the service can reach the database and SQS.

## Search Logic

The handler performs the following:

1. **Load query vector** from the `embeddings` table for the given `image_asset_id`.
2. **Run pgvector cosine search** against `reference_embeddings`, joined with `reference_images`, `reference_items`, `reference_dataset_members`, and `reference_dataset_versions`.
3. **Apply filters**:
   - `region_code` -- like-for-like comparison (e.g., only match "logo" regions against "logo" references).
   - `embedding_model_version` -- only compare vectors produced by the same model.
   - Dataset membership -- `include_in_search = TRUE` and non-retired datasets only.
4. **Split results** into `authentic_matches` and `counterfeit_matches`, returning the top-k of each (default k=5).
5. **Compute scores**:
   - `authentic_cluster_score` -- aggregate similarity to authentic references.
   - `counterfeit_cluster_score` -- aggregate similarity to counterfeit references.
   - `ood_score` -- out-of-distribution score indicating how far the query is from all references.
6. **Stub fallback** -- if no reference embeddings exist, returns stub scores with a warning log.

## Events Consumed

| Event | Queue | Description |
|---|---|---|
| `EMBEDDING_GENERATED` | `vector-search-queue` | Triggers similarity search for a newly generated embedding. |

## Events Published

| Event | Queue | Payload |
|---|---|---|
| `VECTOR_SEARCH_COMPLETED` | `region-scoring-queue` | Includes `authentic_cluster_score`, `counterfeit_cluster_score`, and `ood_score`. |

## Database Tables

| Table | Access | Purpose |
|---|---|---|
| `image_assets` | Read | Look up image metadata and region code. |
| `embeddings` | Read | Retrieve the query embedding vector. |
| `reference_embeddings` | Read | Search target -- reference vectors for cosine similarity. |
| `reference_images` | Read | Metadata for reference images (authentic/counterfeit label). |
| `reference_items` | Read | Item-level metadata for references. |
| `reference_dataset_members` | Read | Dataset membership and `include_in_search` flag. |
| `reference_dataset_versions` | Read | Dataset version and retirement status. |
| `processing_runs` | Read/Write | Idempotency tracking. |

## S3 Usage

This service does not access S3 directly. All data is read from the database.

## Configuration

| Setting | Description |
|---|---|
| `sqs_vector_search_queue` | SQS queue URL for incoming search requests. |
| `sqs_region_scoring_queue` | SQS queue URL for publishing search results downstream. |
| `top_k` | Number of matches to return per category (default: 5). |

## Local Development

```bash
cd services/vector-search-service

pip install -e ".[dev]"

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8204 --reload

# Run the worker
python -m app.worker
```

Requires PostgreSQL with the pgvector extension and seeded reference data.

## Observability

- Structured logs include `image_asset_id`, match counts, and computed scores.
- Logs a warning when falling back to stub results due to empty reference data.
- Audit event `VECTOR_SEARCH_COMPLETED` is recorded for every successful search.

## Idempotency

Key format: `{image_id}|VECTOR_SEARCH|seed_v0.1.0|stub_embedder_v0.1.0`

The key includes both the reference dataset version and the embedding model version to ensure reprocessing occurs when either changes.

## Security Notes

- Cosine similarity queries can be computationally expensive. The pgvector index should be properly configured to avoid sequential scans on large reference sets.
- No raw image data flows through this service; only numeric vectors and scores.
- S3 access is not required by this service.

## Current Limitations

- Falls back to stub scores with a warning if no reference embeddings exist. This is intentional for early development but means the pipeline can produce meaningless results in an unseeded environment.
- Only cosine similarity is supported; no other distance metrics are available.
- The `top_k` parameter is global; per-region or per-category top-k is not supported.
- No approximate nearest neighbor (ANN) index tuning is exposed. Performance depends on pgvector index configuration at the database level.

## Related Documentation

- [Embedding Service](../embedding-service/README.md) -- preceding pipeline stage.
- [Region Scoring Service](../region-scoring-service/README.md) -- next pipeline stage after vector search.
