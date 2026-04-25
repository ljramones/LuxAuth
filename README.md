# LuxAuth

Private monorepo for AI-assisted luxury goods authentication.

The system uses controlled microscopic imaging and machine learning to compare
manufacturing signatures against a curated reference database. It is designed as an
evidence-processing and similarity-scoring platform — not a simple real/fake classifier.

> **This repository is private.** It contains proprietary authentication logic,
> dataset governance tooling, and ML pipeline infrastructure. Do not share externally.

## Repository Structure

```text
luxuryAuthentication/
├── auth-platform/       Backend services, evidence pipeline, ML, capture APIs
├── iphone-app/          Future iPhone capture client
├── android-app/         Future Android capture client
├── docs/                Repo-level documentation
├── ConceptOfOperation.md
├── OverallSystemDesign.md
└── targetArchitecture.md
```

See [docs/repo-structure.md](docs/repo-structure.md) for details.

## auth-platform (Backend)

The backend is a monorepo of 13 Python/FastAPI microservices running in Docker Compose
with PostgreSQL+pgvector, LocalStack (S3/SQS), and an event-driven processing pipeline.

Current capabilities:
- Queue-driven evidence pipeline: upload → quality → normalization → embedding → vector search → scoring → decision
- Real image validation, quality metrics (OpenCV), and normalized PNG derivatives
- 128-dim texture baseline embeddings with pgvector cosine similarity search
- Local PyTorch metric-learning training prototype (CPU, no GPU required)
- Reference dataset governance with versioning, train/test splits, and label provenance
- Evaluation harness with per-model metrics, threshold calibration, and comparison reports
- ML diagnostics: embedding analysis, nearest-neighbor inspection, PCA projection export
- Device-agnostic capture intake APIs (for future mobile/desktop/Pi clients)
- Manifest-based lab capture batch validation, ingestion, and dataset promotion
- Idempotent processing, correlation IDs, structured logging, full audit trail

```bash
cd auth-platform
docker compose up --build -d
make health
make smoke
```

See [auth-platform/README.md](auth-platform/README.md) for the full backend guide.

## Mobile Capture Clients (Planned)

`iphone-app/` and `android-app/` are peer directories beside auth-platform for future capture clients.

**The backend is device-agnostic by design.** It accepts captured evidence and metadata
via HTTP APIs. It does not control microscope hardware. Device-specific microscope
interaction (USB, Bluetooth, vendor SDKs) belongs in the capture clients, not the backend.

The capture client will:
- Connect to a microscope (vendor-specific)
- Guide the operator through a capture protocol
- Upload images to the capture-intake-service API
- Display capture session status and region completeness

## Public External Datasets

LuxAuth includes a controlled external-dataset workflow for evaluating the image pipeline,
texture embeddings, vector search, ML diagnostics, and dataset-governance tooling before
real microscope captures are available.

External datasets are staged locally under `datasets/external/`. This folder is gitignored —
**third-party dataset images must not be committed to the repository.**

| Dataset | Purpose | LuxAuth Use |
|---|---|---|
| LeaData | Microscopic leather texture images | Validate leather-grain embedding behavior and nearest-neighbor search |
| FabricNET | Microscopic woven fabric images | Validate fabric/canvas-like texture embeddings |

These datasets are **not** authentic-vs-counterfeit luxury datasets. They validate pipeline
and material-texture behavior only, not luxury authentication performance.

Documentation:
- [Public Dataset Evaluation Plan](docs/datasets/public-dataset-evaluation-plan.md)
- [License Notes](docs/datasets/public-dataset-license-notes.md)
- [Storage Policy](docs/datasets/dataset-storage-policy.md)
- [LeaData](docs/datasets/leadata.md) · [FabricNET](docs/datasets/fabricnet.md)
- [Manifest Templates](datasets/manifests/README.md) · [Dataset Staging](datasets/README.md)

## Architecture Decisions

| Decision | Status | Rationale |
|---|---|---|
| SageMaker | Deferred | Model lifecycle not stable; throughput unknown; focus on evidence pipeline |
| Kubernetes | Deferred | Docker Compose sufficient for local dev; ECS Fargate for future AWS deploy |
| Terraform | Deferred | Infrastructure-as-code added when AWS deployment begins |
| GPU training | Optional | CPU training works for prototype; GPU needed for real dataset scale |
| Frontend UI | Deferred | Backend APIs are complete; mobile client is the priority UI |

## Security

- **No secrets in this repository.** See [docs/security-and-secrets.md](docs/security-and-secrets.md).
- Environment variables for all credentials
- `.env` files are gitignored
- LocalStack uses test credentials for local development only

## Documentation

| Document | Purpose |
|---|---|
| [ConceptOfOperation.md](ConceptOfOperation.md) | Product and technical concept |
| [docs/roadmap.md](docs/roadmap.md) | Development roadmap |
| [docs/repo-structure.md](docs/repo-structure.md) | Repository layout |
| [docs/security-and-secrets.md](docs/security-and-secrets.md) | Secrets policy |
| [docs/operations/microscope-acceptance-runbook.md](docs/operations/microscope-acceptance-runbook.md) | Microscope setup guide |
| [docs/operations/capture-quality-guide.md](docs/operations/capture-quality-guide.md) | Image capture best practices |
| [auth-platform/README.md](auth-platform/README.md) | Backend developer guide |
| [auth-platform/docs/OverallSystemDesign.md](auth-platform/docs/OverallSystemDesign.md) | Backend system plan |
| [auth-platform/docs/targetArchitecture.md](auth-platform/docs/targetArchitecture.md) | AWS target architecture |
