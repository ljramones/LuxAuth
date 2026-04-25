# Target AWS Architecture

## MVP Without SageMaker, SageMaker Deferred for Later ML Maturity

The target architecture should begin as a **containerized microservice platform on AWS**, with the AI/ML components implemented as Python services. SageMaker should **not** be part of the initial MVP. The first priority is to prove the evidence pipeline: capture, upload, quality control, normalization, embedding generation, vector search, region scoring, and decision auditability.

The backend should be designed around the metric-learning model described in the planning notes: images are transformed into embeddings, compared against a reference database, and combined across multiple image regions to produce an authentication decision. This is more defensible than a simple “CNN says real/fake” classifier. 

---

## 1. Architecture Principle

The system should be designed as an **evidence-processing and similarity-scoring platform**, not as a thin wrapper around an ML endpoint.

Core principle:

> Every authentication decision must be reproducible from stored evidence, scan recipe, device calibration, preprocessing version, embedding model version, reference dataset version, scoring rules, and audit history.

This means the backend must preserve:

```text
raw image evidence
normalized image derivatives
capture metadata
device metadata
scan recipe version
image quality results
embedding model version
nearest-neighbor match results
region-level scores
decision-rule version
final decision
audit trail
```

---

# 2. Revised High-Level Architecture

```text
Mobile App / Capture Device
        ↓
CloudFront + AWS WAF
        ↓
API Gateway or Application Load Balancer
        ↓
ECS Fargate Microservices
        ↓
S3 Evidence Storage
        ↓
SQS / EventBridge Processing Pipeline
        ↓
Python ML Services on ECS Fargate
        ↓
RDS PostgreSQL + pgvector
        ↓
Decision Engine
        ↓
Review Console / Certificate Service
```

For the MVP, the architecture should be:

```text
No SageMaker
No EKS
No GPU dependency
No managed ML platform dependency
```

Instead:

```text
Python FastAPI ML containers
PyTorch / OpenCV / NumPy
ECS Fargate
S3
RDS PostgreSQL
pgvector
SQS
EventBridge
CloudWatch
OpenTelemetry / X-Ray
CloudTrail
```

---

# 3. Why SageMaker Is Deferred

SageMaker is powerful, but it solves a later-stage problem. The early platform problem is not “how do we host a massive model at scale?” The early problem is:

```text
Can we collect reliable microscopic evidence?
Can we normalize it consistently?
Can we generate useful embeddings?
Can we compare against reference examples?
Can we produce a defensible authentication decision?
Can we audit every decision?
```

Those questions can be answered without SageMaker.

## Reasons to Defer SageMaker

| Reason                              | Explanation                                                                                                           |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Model shape is not yet stable       | Early experiments may use different CNNs, ViTs, embedding dimensions, preprocessing methods, and scoring logic.       |
| Throughput is unknown               | We do not yet know scan volume, inference latency needs, or GPU requirements.                                         |
| The hard part is the data pipeline  | Dataset quality, capture consistency, labels, and region scoring matter more than managed ML hosting at first.        |
| ECS is simpler for MVP              | Python ML containers can run directly on ECS Fargate with fewer moving parts.                                         |
| Lower operational complexity        | No SageMaker endpoint lifecycle, model package registry, inference variants, or training-job governance required yet. |
| Better debugging early              | FastAPI containers are easier to instrument, test locally, inspect, and iterate during the prototype stage.           |
| Avoid premature platform commitment | The system may later choose SageMaker, EKS GPU services, Triton, or another serving layer based on real requirements. |

The architecture should therefore treat SageMaker as an **evolutionary addition**, not a foundational dependency.

---

# 4. MVP Compute Architecture

## 4.1 ECS Fargate as Primary Runtime

Use **ECS Fargate** for the initial microservices.

Services run as independent containers:

```text
scan-session-service
scan-recipe-service
evidence-asset-service
device-service
image-quality-service
image-normalization-service
region-classifier-service
embedding-service
vector-search-service
region-scoring-service
decision-service
review-service
certificate-service
audit-service
```

This gives us:

* Independent deployability
* Containerized Python ML services
* Clear service boundaries
* AWS-native scaling
* Good observability through CloudWatch and OpenTelemetry
* No Kubernetes overhead
* No SageMaker dependency

---

# 5. Revised Service Architecture

## 5.1 Business Workflow Services

| Service                | Responsibility                                              |
| ---------------------- | ----------------------------------------------------------- |
| Organization Service   | Tenants, reseller accounts, users, roles                    |
| Device Service         | Registered devices, calibration profile, device trust level |
| Scan Session Service   | Lifecycle of an authentication attempt                      |
| Scan Recipe Service    | Required image regions by brand/category/material           |
| Evidence Asset Service | Raw image storage, upload URLs, image metadata              |
| Decision Service       | Final authentication decision from scored evidence          |
| Certificate Service    | Hosted certificate generation and verification              |
| Review Service         | Human expert review and label correction                    |
| Audit Service          | Append-only business audit trail                            |

## 5.2 Python AI/ML Services

| Service                   | Responsibility                                                         |
| ------------------------- | ---------------------------------------------------------------------- |
| Image Quality Service     | Blur, exposure, glare, focus, compression, field coverage              |
| Normalization Service     | Lens correction, scale normalization, color normalization, crop/resize |
| Region Classifier Service | Confirms the image shows the requested region                          |
| Embedding Service         | Runs PyTorch model and produces vector embeddings                      |
| Vector Search Service     | Searches authentic/counterfeit reference embeddings                    |
| Region Scoring Service    | Produces per-region similarity and anomaly scores                      |
| Model Metadata Service    | Tracks model version, preprocessing version, dataset version           |

The embedding service remains a normal Python container during MVP:

```text
FastAPI
PyTorch
OpenCV
NumPy
Pydantic
boto3
```

---

# 6. Revised AWS Infrastructure

## 6.1 Front Door

```text
Route 53
  ↓
CloudFront
  ↓
AWS WAF
  ↓
API Gateway or Application Load Balancer
```

Use this for:

* Public API traffic
* Mobile app calls
* Review console access
* Certificate lookup pages

---

## 6.2 Application Runtime

```text
ECS Fargate
  ├── business services
  ├── evidence services
  ├── Python ML services
  ├── scoring services
  └── review/certificate services
```

For MVP, ECS Fargate is enough.

Later, if GPU inference becomes necessary, the architecture can add one of:

```text
ECS on GPU-backed EC2
EKS with GPU node groups
SageMaker endpoints
```

But not yet.

---

## 6.3 Storage

| Data                    | AWS Service                              |
| ----------------------- | ---------------------------------------- |
| Raw uploaded images     | S3                                       |
| Normalized images       | S3                                       |
| Reference image library | S3                                       |
| Model artifacts         | S3                                       |
| Business metadata       | RDS PostgreSQL                           |
| Embeddings MVP          | RDS PostgreSQL + pgvector                |
| Audit events            | PostgreSQL append-only table + S3 export |
| Logs                    | CloudWatch Logs                          |
| Secrets                 | Secrets Manager                          |
| Encryption keys         | KMS                                      |

Initial vector search should use:

```text
RDS PostgreSQL + pgvector
```

This is enough for the MVP and avoids introducing OpenSearch too early.

Later, if the reference library becomes large, move vector search to:

```text
Amazon OpenSearch Serverless vector search
```

---

## 6.4 Event Processing

Use:

```text
EventBridge for domain events
SQS for durable work queues
DLQs for failed processing
```

Example event flow:

```text
ImageUploaded
  ↓
ImageQualityRequested
  ↓
ImageQualityCompleted
  ↓
ImageNormalizationRequested
  ↓
ImageNormalized
  ↓
EmbeddingRequested
  ↓
EmbeddingGenerated
  ↓
VectorSearchCompleted
  ↓
RegionScored
  ↓
AuthenticationDecisionCreated
```

Every processing stage should be idempotent.

Use an idempotency key like:

```text
imageId + stage + modelVersion + preprocessingVersion
```

Example:

```text
img_123:EMBEDDING:leather_embedder_v0.3.1:normalize_v2
```

---

# 7. Revised MVP Architecture Diagram

```text
Mobile App / Microscope Device
        ↓
API Gateway / ALB
        ↓
ECS Fargate
  ├── scan-session-service
  ├── scan-recipe-service
  ├── device-service
  ├── evidence-asset-service
  ├── image-quality-service
  ├── normalization-service
  ├── embedding-service
  ├── vector-search-service
  ├── region-scoring-service
  ├── decision-service
  ├── review-service
  └── certificate-service
        ↓
S3
  ├── raw-evidence
  ├── normalized-evidence
  ├── reference-library
  └── model-artifacts
        ↓
RDS PostgreSQL
  ├── scan metadata
  ├── device metadata
  ├── recipe metadata
  ├── quality reports
  ├── embeddings via pgvector
  ├── region scores
  ├── decisions
  └── audit events
        ↓
SQS / EventBridge
        ↓
CloudWatch + OpenTelemetry/X-Ray + CloudTrail
```

---

# 8. Where SageMaker Fits Later

SageMaker should be added when the system matures into a true ML operations platform.

## Add SageMaker When One or More of These Become True

| Trigger                                       | Why SageMaker Helps                                             |
| --------------------------------------------- | --------------------------------------------------------------- |
| GPU inference is required                     | Managed GPU-backed endpoints become attractive                  |
| Inference latency is business-critical        | Real-time endpoints can isolate and scale model serving         |
| Scan volume grows significantly               | Autoscaling inference endpoints become useful                   |
| Models need formal approval workflows         | SageMaker Model Registry helps govern promotion                 |
| Training becomes recurring                    | SageMaker Training Jobs can standardize retraining              |
| Batch re-embedding becomes large              | SageMaker Batch Transform can process large reference sets      |
| Multiple production model versions are active | SageMaker supports controlled deployment patterns               |
| ML compliance/governance becomes important    | Model packages, metrics, lineage, and approvals become valuable |

---

# 9. Future SageMaker-Enhanced Architecture

Later, the architecture could evolve to this:

```text
ECS Fargate Business Services
        ↓
SQS / EventBridge
        ↓
SageMaker Inference Endpoints
  ├── image-quality-model
  ├── region-classifier-model
  └── embedding-model
        ↓
OpenSearch Serverless Vector Search
        ↓
Decision Service on ECS
        ↓
Review / Certificate Services
```

And for training:

```text
Reference Dataset in S3
        ↓
SageMaker Training Job
        ↓
Model Evaluation
        ↓
SageMaker Model Registry
        ↓
Approved Production Model
        ↓
Inference Endpoint Deployment
```

This is the right future state, but only after the MVP proves the capture and scoring pipeline.

---

# 10. Architecture Decision Record

## Decision

The MVP will **not use SageMaker**.

The MVP will use:

```text
ECS Fargate
Python FastAPI ML services
PyTorch/OpenCV containers
S3
RDS PostgreSQL + pgvector
SQS/EventBridge
CloudWatch/OpenTelemetry/X-Ray
CloudTrail
```

## Rationale

The early system needs fast iteration, simple debugging, and control over the evidence pipeline. The core challenge is not managed model hosting; it is building a trustworthy capture, evidence, embedding, similarity-search, and decision pipeline.

SageMaker will be introduced later if the platform requires managed GPU inference, formal model registry, recurring training jobs, batch re-embedding, or mature ML governance.

## Consequences

Positive:

* Simpler MVP
* Lower operational complexity
* Faster local and cloud iteration
* Easier debugging of ML services
* No premature dependency on SageMaker deployment patterns
* Keeps architecture portable

Tradeoffs:

* Model governance must be implemented lightly at first
* ECS-hosted inference may need more custom operational work
* GPU inference is deferred
* Large-scale batch training/re-embedding will require later platform expansion

## Future Revisit Criteria

Revisit SageMaker when:

```text
reference image library grows beyond pgvector comfort
embedding model requires GPU inference
model promotion needs formal approval gates
training becomes recurring
batch re-embedding becomes operationally expensive
inference latency becomes a customer-facing SLA issue
```

---

# 11. Final Target Architecture Statement

The target architecture should be:

> An AWS-native, event-driven microservice platform using ECS Fargate for business and Python AI/ML services, S3 for immutable evidence storage, RDS PostgreSQL with pgvector for MVP metadata and vector search, SQS/EventBridge for asynchronous processing, and CloudWatch/OpenTelemetry/CloudTrail for observability and audit. SageMaker is deliberately deferred until the platform requires managed GPU inference, recurring training pipelines, model registry governance, or large-scale batch reprocessing.


