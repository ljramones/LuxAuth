# Target AWS Architecture

This document describes the production AWS architecture that the local Docker Compose stack is designed to mirror.

## Overview

```
                            ┌──────────────┐
                            │  CloudFront  │
                            │   + WAF      │
                            └──────┬───────┘
                                   │
                            ┌──────┴───────┐
                            │  API Gateway │
                            │  / ALB       │
                            └──────┬───────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                  ECS Fargate Cluster               │
         │                                                    │
         │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
         │  │ scan-   │ │ device- │ │ recipe- │ │evidence-│ │
         │  │ session │ │ service │ │ service │ │ asset   │ │
         │  └────┬────┘ └─────────┘ └─────────┘ └────┬────┘ │
         │       │                                     │      │
         │       │         ┌──────────┐                │      │
         │       │         │   SQS    │◄───────────────┘      │
         │       │         │  Queues  │                       │
         │       │         └────┬─────┘                       │
         │       │              │                              │
         │  ┌────┴────┐ ┌──────┴──┐ ┌─────────┐ ┌─────────┐ │
         │  │ image-  │ │ normal- │ │embedding│ │ vector- │ │
         │  │ quality │ │ ization │ │ service │ │ search  │ │
         │  └─────────┘ └─────────┘ └─────────┘ └────┬────┘ │
         │                                            │      │
         │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │      │
         │  │ region- │ │decision-│ │ review- │      │      │
         │  │ scoring │ │ service │ │ service │      │      │
         │  └─────────┘ └─────────┘ └─────────┘      │      │
         │                                            │      │
         │  ┌─────────┐                               │      │
         │  │certific-│                               │      │
         │  │  ate    │                               │      │
         │  └─────────┘                               │      │
         └────────────────────────────────────────────┘      │
                   │                                          │
         ┌────────┴────────┐                    ┌────────────┴─┐
         │  RDS PostgreSQL │                    │   Amazon S3  │
         │   + pgvector    │                    │  (evidence)  │
         └─────────────────┘                    └──────────────┘
```

## Compute — ECS Fargate

All 12 microservices run as ECS Fargate tasks. Each service has its own task definition with independently tunable CPU/memory. Services are placed behind an internal ALB for synchronous HTTP communication and subscribe to SQS queues for async pipeline processing.

## Storage — Amazon S3

Evidence images (raw uploads, normalized, thumbnails) are stored in S3 with lifecycle policies. Bucket structure mirrors the LocalStack setup: `auth-platform-evidence-assets`.

## Database — RDS PostgreSQL + pgvector

A single RDS PostgreSQL instance with the pgvector extension hosts all service schemas. Each service uses its own schema namespace. Vector similarity search (`<=>` cosine distance) powers the reference-matching step.

## Messaging — SQS + EventBridge

- **SQS queues** carry pipeline events between services (ImageUploaded, ImageQualityCompleted, etc.).
- **EventBridge** provides higher-level orchestration, fan-out to analytics, and dead-letter routing.

## Observability — CloudWatch + OpenTelemetry / X-Ray

- Each service is instrumented with the OpenTelemetry SDK.
- Traces export to AWS X-Ray via the OTLP exporter.
- Metrics and structured logs ship to CloudWatch.
- Dashboards track pipeline throughput, latency per stage, and error rates.

## Audit — CloudTrail

All API calls and S3 access are logged via CloudTrail for compliance and forensic audit.

## Edge — CloudFront + WAF

Public API endpoints sit behind CloudFront with WAF rules for rate limiting, geo-blocking, and bot mitigation.

## ML Inference — SageMaker (Deferred)

SageMaker is the intended home for embedding generation and scoring models once the model lifecycle stabilizes. See [ADR-0001](adr-0001-defer-sagemaker.md). For MVP, inference runs in the same Fargate containers as the rest of the application logic.
