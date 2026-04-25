# ADR-0001: Defer SageMaker for MVP

## Status

Accepted

## Date

2026-04-24

## Context

We are building an MVP authentication platform that uses ML models to generate image embeddings and score product regions for authenticity. AWS SageMaker is the natural choice for managed ML inference in production, offering model hosting, autoscaling, GPU instances, model registry, and batch transform.

However, at this stage:

- The ML model architecture is not finalized. We are still experimenting with embedding models and scoring approaches.
- Throughput requirements are unknown. We do not yet have data on how many authentications per hour we need to support.
- The evidence pipeline (image upload through decision) is the primary engineering risk and needs to be built and validated first.
- The team is small and needs to minimize the number of AWS services to learn and debug simultaneously.

## Decision

Use standard Python/FastAPI containers running on ECS Fargate for all ML inference (embedding generation, vector search, region scoring) instead of SageMaker endpoints. Models are loaded at container startup and run inference in-process.

## Rationale

- **Simpler debugging:** ML code runs in the same container as the API, with the same logging and tracing. No separate SageMaker logs to correlate.
- **Faster iteration:** Deploying a model change is the same as deploying any other code change — push a new container image.
- **Lower complexity:** No SageMaker endpoint configuration, model artifacts in S3, inference pipelines, or autoscaling policies to manage.
- **Focus on the pipeline:** The hard problem right now is getting the evidence pipeline correct — image quality, normalization, embedding, search, scoring, decision. The compute substrate for inference is secondary.
- **Cost predictability:** Fargate pricing is straightforward. SageMaker endpoint pricing (especially with GPU instances) adds uncertainty.

## Consequences

### Positive

- Developers can run the full pipeline locally with Docker Compose with no SageMaker emulation needed.
- Model iteration cycle is fast: change code, rebuild container, test.
- Fewer AWS services to configure and monitor.

### Tradeoffs

- No managed model registry — model versions are tracked via container image tags.
- No managed GPU instances — CPU inference only for MVP, which limits model size and throughput.
- No built-in A/B testing or shadow deployment for models.
- Manual scaling — must tune Fargate task count rather than relying on SageMaker autoscaling.

## Revisit When

- **GPU is required:** Model accuracy improves significantly with larger models that need GPU inference.
- **Recurring training:** We establish a training pipeline and need managed training jobs.
- **Model registry:** Multiple model versions need to coexist with controlled rollout.
- **Batch re-embedding:** Reference database needs periodic re-embedding when models change.
- **Inference SLA requires autoscaling:** Traffic patterns require request-based autoscaling rather than fixed task count.
