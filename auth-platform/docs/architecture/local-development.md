# Local Development

## How Local Dev Mirrors AWS

The Docker Compose stack is designed so that every local component maps to an AWS service. Code that talks to S3, SQS, or PostgreSQL uses the same SDKs and client libraries in both environments — only endpoint URLs and credentials differ, controlled by environment variables.

## Docker Compose Stack

The stack consists of:

- **postgres** — pgvector/pgvector:pg16 image with init scripts that create schemas, enable the vector extension, and seed reference data.
- **localstack** — LocalStack v3 providing S3 and SQS. Init scripts in `infra/localstack/init/` create buckets and queues on startup.
- **pgadmin** (optional, `tools` profile) — Web-based database browser.
- **12 application services** — Each built from its own Dockerfile under `services/`.

All services share a common Docker Compose extension (`x-service-common`) that wires up the database URL, AWS endpoint, log level, and shared library volume.

## LocalStack Services

| Service | Purpose |
|---|---|
| S3 | Evidence image storage (bucket: `auth-platform-evidence-assets`) |
| SQS | Async event pipeline between services |

## Database Setup

PostgreSQL starts with init scripts mounted from `infra/postgres/init/`. These scripts:

1. Enable the `vector` extension.
2. Create tables for each service's domain.
3. Seed reference data (organizations, devices, reference embeddings).

The database is accessible at `localhost:5432` with credentials `authplatform` / `authplatform`.

## How to Reset State

```bash
make down    # stops all containers and removes volumes (including DB data)
make up      # rebuilds and starts fresh
```

This gives you a clean database with seed data and empty S3 buckets/SQS queues.

## Port Assignments

| Port | Service |
|---|---|
| 4566 | LocalStack (S3, SQS) |
| 5050 | pgAdmin (tools profile only) |
| 5432 | PostgreSQL |
| 8101 | scan-session-service |
| 8102 | scan-recipe-service |
| 8103 | device-service |
| 8104 | evidence-asset-service |
| 8201 | image-quality-service |
| 8202 | normalization-service |
| 8203 | embedding-service |
| 8204 | vector-search-service |
| 8205 | region-scoring-service |
| 8301 | decision-service |
| 8302 | review-service |
| 8303 | certificate-service |

## Debugging Tips

**Attach to a running container:**
```bash
docker exec -it auth-platform-scan-session-service /bin/bash
```

**Check logs for a single service:**
```bash
docker compose logs -f scan-session-service
```

**Check all logs:**
```bash
make logs
```

**Access pgAdmin:**
Open `http://localhost:5050` in your browser. Login with `admin@authplatform.local` / `admin`. Add a server connection to host `postgres`, port `5432`, user `authplatform`, password `authplatform`.

**Inspect LocalStack resources:**
```bash
# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List SQS queues
aws --endpoint-url=http://localhost:4566 sqs list-queues

# Read messages from a queue (without consuming)
aws --endpoint-url=http://localhost:4566 sqs receive-message \
  --queue-url http://localhost:4566/000000000000/image-uploaded
```

**Connect to the database directly:**
```bash
psql -h localhost -U authplatform -d authplatform
```

## Queue-Driven Pipeline

In local development, each processing service runs an SQS worker loop as a background task alongside its FastAPI HTTP server. The worker polls its assigned queue, processes messages, and publishes to the next queue.

### Observing the pipeline

Watch logs for all services:
```bash
make logs
```

Worker activity appears as `processing_message` and `message_processed` log entries.

### Direct HTTP endpoints

All services retain their direct HTTP `/process/{id}` endpoints for debugging. These bypass the queue and execute processing synchronously.

## Dataset Governance & Evaluation

### Creating a dataset version

```bash
make generate-synthetic-data     # Create synthetic images
make ingest-reference-data DATASET=synthetic_lv_monogram_v0.1.0 FORCE=1
                                 # Ingest with dataset version, splits, labels
```

This creates dataset `synthetic_lv_monogram_v0.1.0` with:
- 30 reference images (15 authentic, 15 counterfeit)
- Train/validation/test splits
- Label reviews for provenance tracking

### Running an evaluation

```bash
make run-evaluation              # Evaluate test split against search references
make evaluation-report           # Print human-readable report
```

### Inspecting data

```sql
-- Dataset versions
SELECT dataset_version, status, source_type FROM reference_dataset_versions;

-- Split distribution
SELECT split, count(*) FROM reference_dataset_members GROUP BY split;

-- Active threshold profile
SELECT profile_name, strong_match_threshold, mismatch_threshold FROM threshold_profiles WHERE status = 'active';

-- Latest evaluation
SELECT evaluation_name, status, summary_json FROM evaluation_runs ORDER BY started_at DESC LIMIT 1;
```

### Idempotency

Processing is idempotent. Running `make smoke` multiple times is safe — duplicate processing is detected and skipped via the `processing_runs` table.

### Inspecting queues

```bash
# List all queues
aws --endpoint-url=http://localhost:4566 sqs list-queues

# Check dead-letter queue
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/dead-letter-queue \
  --attribute-names ApproximateNumberOfMessages
```
