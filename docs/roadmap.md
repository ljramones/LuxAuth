# Development Roadmap

## Completed

### Phase 1-3: Backend Scaffold + Event Pipeline
- 13 FastAPI microservices in Docker Compose
- PostgreSQL + pgvector, LocalStack S3/SQS
- Queue-driven evidence pipeline with idempotency and correlation IDs
- Scan recipe resolution, canonical region codes, evidence upload validation
- Completeness-aware decision rules, structured audit trail

### Phase 4: Real Image Evidence + Baseline Embeddings
- Real image validation (Pillow/OpenCV)
- Image quality metrics: sharpness, exposure, glare detection
- 512x512 normalized PNG derivatives
- texture_baseline_v0.1.0: 128-dim hand-crafted texture embeddings
- Real pgvector cosine similarity search

### Phase 5: Dataset Governance + Evaluation Harness
- Reference dataset versions with train/validation/test splits
- Label provenance and confidence tracking
- Threshold profiles (DB-backed)
- Reproducible evaluation runs with per-item metrics
- Comparison reports across model versions

### Phase 6: Local Metric Learning Training
- PyTorch ResNet18 + contrastive loss training (CPU)
- Model artifact export to S3 with metadata
- Multi-model embedding service backend
- Re-embedding and per-model evaluation

### Phase 7: ML Diagnostics + Calibration
- Embedding distribution analysis and cluster separation
- Nearest-neighbor inspection with JSON export
- Threshold sweep and calibration
- PCA projection export for visualization
- Multi-model comparison (3+ models)

### Phase 8A: Capture Intake APIs
- Device-agnostic capture-intake-service (port 8106)
- Protocol-driven capture sessions with region completeness
- Device registration and calibration APIs

### Phase 8B: Capture Batch Ingestion
- YAML manifest-based lab capture workflow
- Validation, ingestion, and dataset promotion scripts
- Leakage checks (SHA-256 cross-split detection)
- Safety guard: smoke_* prefix for test data, --force for real data

### Phase 8C: Operator Readiness
- Microscope acceptance runbook
- First real capture checklist
- Capture quality guide
- Manifest template generator

## Next

### Microscope Acquisition + First Real Captures
- Acquire Dino-Lite or equivalent microscope
- Follow microscope acceptance runbook
- Capture first real reference images
- Build first real dataset version
- Evaluate baseline on real data

### Mobile Capture Client (iOS)
- Swift/SwiftUI iPhone app
- USB microscope integration via vendor SDK
- Guided capture workflow following protocol regions
- Upload to capture-intake-service API
- Session status and completeness display

### Model Improvement
- Longer training on real data
- Pretrained backbone (ImageNet weights)
- Hard negative mining
- Per-region model specialization
- Threshold calibration on real validation set

### AWS Deployment (When Ready)
- ECS Fargate for services
- RDS PostgreSQL + pgvector
- S3 for evidence storage
- SQS for async pipeline
- CloudWatch + OpenTelemetry
- SageMaker (when model lifecycle and throughput warrant it)

## Not Planned Yet
- Public API
- Multi-tenant SaaS
- Brand partnership integrations
- Certificate blockchain/NFT
- Real-time mobile inference
