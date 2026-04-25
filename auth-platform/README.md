# Auth Platform — Luxury Product Authentication Backend

An AI-assisted authentication platform that compares microscopic manufacturing signatures against a reference database of known-authentic products. This is an evidence-processing and similarity-scoring platform, not a simple binary classifier. Each image undergoes quality assessment, normalization, embedding generation, vector search against reference data, per-region scoring, and a final weighted decision that produces a confidence-scored authentication verdict with full evidence lineage.

## Architecture Overview

The platform is composed of **12 Python/FastAPI microservices** organized into four domains. Data is persisted in **PostgreSQL with pgvector** for embedding similarity search. Object storage (images) and async messaging use **LocalStack** (S3 + SQS) locally, mapping directly to AWS services in production. Everything runs in **Docker Compose** for local development.

### Why SageMaker Is Deferred

Model lifecycle is not yet stable, throughput requirements are unknown, and the immediate priority is getting the evidence pipeline correct end-to-end. ML inference runs inside standard FastAPI containers for now. See [ADR-0001](docs/architecture/adr-0001-defer-sagemaker.md) for the full rationale.

## Services

| Service | Port | Domain | Description |
|---|---|---|---|
| scan-session-service | 8101 | Operational | Creates and tracks authentication sessions |
| scan-recipe-service | 8102 | Operational | Defines which regions/angles to capture per product type |
| device-service | 8103 | Operational | Registers and manages capture devices |
| evidence-asset-service | 8104 | Evidence | Receives uploaded images, stores in S3 |
| image-quality-service | 8201 | Evidence | Assesses image sharpness, lighting, blur |
| normalization-service | 8202 | Evidence | Crops, resizes, color-corrects images |
| embedding-service | 8203 | ML | Generates vector embeddings from normalized images |
| vector-search-service | 8204 | ML | Searches pgvector for similar reference embeddings |
| region-scoring-service | 8205 | ML | Scores authenticity per region based on similarity |
| decision-service | 8301 | Trust | Aggregates region scores into a final verdict |
| review-service | 8302 | Trust | Human review queue for low-confidence decisions |
| certificate-service | 8303 | Trust | Issues authentication certificates |

## Event Flow

```
ImageUploaded
  → ImageQualityCompleted
    → ImageNormalized
      → EmbeddingGenerated
        → VectorSearchCompleted
          → RegionScored
            → AuthenticationDecisionCreated
```

Each event is published to SQS and consumed by the next service in the pipeline. See [Event Flow](docs/architecture/event-flow.md) for the full diagram.

## Quick Start

### Prerequisites

- Docker Desktop (with Docker Compose v2)
- Python 3.12+
- `make`

### Getting Started

```bash
cp .env.example .env    # create local env config
make up                 # build and start all services
make smoke              # run the end-to-end smoke test
```

### Makefile Targets

| Target | Description |
|---|---|
| `make up` | Build and start all containers |
| `make down` | Stop containers and remove volumes |
| `make logs` | Tail logs from all containers |
| `make ps` | Show container status |
| `make init` | Start only postgres + localstack |
| `make test` | Run pytest |
| `make lint` | Run ruff check |
| `make format` | Run ruff format |
| `make smoke` | Run end-to-end smoke test pipeline |
| `make clean` | Stop containers, remove volumes and images |

## Running a Smoke Test

The smoke test creates a scan session, uploads a sample image, and walks it through every pipeline stage:

```bash
make smoke
# or directly:
python scripts/run_local_pipeline.py
```

The script prints each step with status indicators and ends with the final authentication decision.

## How to Add a New Service

1. Copy an existing service directory (e.g., `services/region-scoring-service`).
2. Rename the directory and update `SERVICE_NAME` / `SERVICE_PORT` in the code.
3. Choose the next available port in the appropriate range (81xx Capture, 82xx Analysis, 83xx Decision).
4. Add the service block to `docker-compose.yml` following the existing pattern.
5. If the service participates in the event pipeline, subscribe it to the appropriate SQS queue.

## Local vs AWS Mapping

| Local (Docker Compose) | AWS Production |
|---|---|
| Docker Compose | ECS Fargate |
| LocalStack S3 | Amazon S3 |
| LocalStack SQS | Amazon SQS |
| PostgreSQL container | Amazon RDS PostgreSQL |
| pgvector extension | pgvector on RDS |
| — | EventBridge (orchestration) |
| — | CloudFront + WAF (API gateway) |
| — | CloudWatch + X-Ray (observability) |
| — | CloudTrail (audit) |

## Observability (Deferred)

Tracing is planned via OpenTelemetry instrumentation of each FastAPI service, with OTLP exporters shipping to an OpenTelemetry Collector. In production this maps to AWS X-Ray. For MVP, services log structured JSON to stdout and rely on `docker compose logs` for debugging. The instrumentation points are:
- FastAPI middleware (request/response spans)
- httpx outbound calls
- SQLAlchemy queries
- S3/SQS client calls

## When the Microscope Arrives

When a real microscope becomes available, follow the acceptance workflow:

1. **[Microscope Acceptance Runbook](../docs/operations/microscope-acceptance-runbook.md)** — step-by-step from device registration through evaluation diagnostics
2. **[First Real Capture Checklist](../docs/operations/first-real-capture-checklist.md)** — quick reference checklist
3. **[Capture Quality Guide](../docs/operations/capture-quality-guide.md)** — how to get better microscope images

### Quick Start

```bash
# Generate a manifest template from the active protocol
python3 scripts/create_capture_manifest_template.py \
  --batch-code lab_first_real_batch_001 \
  --device-code YOUR_DEVICE_SERIAL \
  --output sample_data/lab_captures/lab_first_real_batch_001/manifest.yaml

# Then: capture images, edit manifest, and run:
make validate-capture-batch BATCH=lab_first_real_batch_001
make ingest-capture-batch BATCH=lab_first_real_batch_001
make promote-capture-batch BATCH=lab_first_real_batch_001 DATASET=lab_first_real_v0.1.0
make run-evaluation
make evaluation-report
```

### Data Categories

| Category | Prefix | Purpose | Example |
|---|---|---|---|
| Smoke test data | `smoke_*` | Pipeline validation, auto-cleaned | `smoke_lab_lv_monogram_batch_001` |
| Synthetic data | `synthetic_*` | Baseline evaluation | `synthetic_lv_monogram_v0.1.0` |
| Real lab data | `lab_*` | Real microscope captures | `lab_first_real_batch_001` |
| Production data | (no prefix) | Future production use | — |

Smoke and synthetic data can be regenerated freely. Real lab data is protected by
a safety guard — destructive operations require `--force` for non-smoke batches.

## Next Steps

- Replace stub ML models with real embedding and scoring models
- Integrate SageMaker for GPU inference when model lifecycle stabilizes
- Build review UI for human-in-the-loop authentication
- Add OpenTelemetry instrumentation
- Production deployment via Terraform/CDK

Mobile capture clients live in `iphone-app/` and `android-app/` at the repo root.
