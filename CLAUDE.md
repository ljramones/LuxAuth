# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI-assisted physical product authentication platform** — a system that uses controlled microscopic imaging and ML to determine whether luxury goods are authentic. The system compares microscopic material/manufacturing signatures against a curated reference database of known authentic and counterfeit samples.

This repository is currently in the **planning/design phase** — it contains concept-of-operations and architecture documents but no application code yet.

## Architecture

The system is designed as an **evidence-processing and similarity-scoring platform**, not a simple classifier. Every authentication decision must be reproducible from stored evidence, model version, reference dataset version, and decision rules.

### Four Backend Domains

1. **Operational Platform** — users, devices, sessions, uploads, scan status
2. **Evidence Processing** — image validation, normalization, metadata, storage
3. **ML / Similarity Platform** — embeddings, vector search, scoring, anomaly detection
4. **Trust / Review / Certification** — human review, results, certificates, audit trail

### Key Design Decisions

- **Metric learning over classification**: Uses embedding models + similarity search against reference clusters, not a binary real/fake CNN
- **Multi-model pipeline**: Image quality → region classifier → brand/material classifier → embedding → vector search → anomaly detection → ensemble decision
- **Region-scoped comparison**: Images are compared like-for-like (e.g., Chanel caviar leather grain vs. Chanel caviar leather grain references)
- **Conservative results**: System returns Verified/Unverified/Inconclusive/Expert Review — never "Fake"
- **SageMaker deferred**: MVP uses ECS Fargate + Python FastAPI for ML services; SageMaker added later when GPU inference or formal model governance is needed

### Target MVP Tech Stack

- **Control plane**: Java/Spring Boot or Go
- **ML plane**: Python, FastAPI, PyTorch, OpenCV
- **Storage**: PostgreSQL + pgvector, S3/MinIO
- **Queue**: SQS/RabbitMQ/Redis Streams
- **Infrastructure**: ECS Fargate (AWS), Docker Compose (local)
- **Mobile app**: Flutter, React Native, or native iOS

### MVP Scope

Start narrow: 1-2 luxury brands, 1 product category, 2-3 materials, fixed scan recipe, fixed imaging profile. Prove the thesis before expanding.

## Key Documents

- `ConceptOfOperation.md` — Full product/technical concept, imaging requirements, ML design, dataset strategy, IP/legal considerations, MVP scope
- `OverallSystemDesign.md` — Backend service architecture, API design, data model, event-driven processing, build slices
- `targetArchitecture.md` — AWS deployment architecture, SageMaker deferral rationale, infrastructure decisions
