# Service Boundaries

## Domains

The platform is organized into four domains, each responsible for a distinct stage of the authentication pipeline.

### Operational Domain

Services that manage sessions, devices, and capture configuration.

| Service | Responsibility |
|---|---|
| scan-session-service (8101) | Creates authentication sessions, tracks their lifecycle from image capture through final decision. |
| scan-recipe-service (8102) | Defines which regions and angles must be captured for each product category (e.g., "Louis Vuitton handbag requires 5 regions"). |
| device-service (8103) | Registers microscope/camera devices, tracks calibration status and capabilities. |

### Evidence Domain

Services that receive, validate, and normalize captured images.

| Service | Responsibility |
|---|---|
| evidence-asset-service (8104) | Receives uploaded images, stores originals in S3, records metadata, emits ImageUploaded events. |
| image-quality-service (8201) | Assesses sharpness, lighting, blur, and resolution; rejects images that cannot produce reliable embeddings. |
| normalization-service (8202) | Crops, resizes, and color-corrects images to a canonical form suitable for embedding generation. |

### ML Domain

Services that generate and compare vector representations of product features.

| Service | Responsibility |
|---|---|
| embedding-service (8203) | Generates a vector embedding from a normalized image using the current model. |
| vector-search-service (8204) | Searches pgvector for the most similar reference embeddings and returns ranked matches. |
| region-scoring-service (8205) | Converts vector similarity results into a per-region authenticity score with confidence bounds. |

### Trust Domain

Services that aggregate evidence into decisions, support human review, and issue certificates.

| Service | Responsibility |
|---|---|
| decision-service (8301) | Aggregates region scores using weighted rules to produce a final AUTHENTIC / SUSPECT / INCONCLUSIVE verdict. |
| review-service (8302) | Manages a queue of low-confidence or flagged decisions for human expert review. |
| certificate-service (8303) | Issues tamper-evident authentication certificates for verified-authentic products. |

### Queue Assignments

| Service | Consumes | Produces To |
|---|---|---|
| evidence-asset-service | — | image-quality-queue |
| image-quality-service | image-quality-queue | normalization-queue |
| normalization-service | normalization-queue | embedding-queue |
| embedding-service | embedding-queue | vector-search-queue |
| vector-search-service | vector-search-queue | region-scoring-queue |
| region-scoring-service | region-scoring-queue | decision-queue |
| decision-service | decision-queue | — |

## Inter-Service Communication

- **Synchronous (HTTP):** Used for queries that need an immediate response — e.g., scan-session-service fetching a scan recipe, or the decision-service reading region scores.
- **Asynchronous (SQS):** Used for the evidence pipeline. Each service publishes a completion event to an SQS queue; the next service in the pipeline consumes it and begins processing. This decouples services and allows independent scaling.
