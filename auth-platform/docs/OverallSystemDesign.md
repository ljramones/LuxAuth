# Backend System Plan

## Entrupy-Like Authentication Platform

## 1. Backend Mission

The backend’s job is to answer this question:

> “Given a set of controlled microscopic images from a physical item, how similar are those images to known authentic and known counterfeit reference samples for the claimed brand, model, material, region, and production period?”

The backend should produce a structured authentication result:

```text
Result: Verified / Unverified / Inconclusive / Expert Review Required

Evidence:
- Region-level scores
- Similarity to authentic reference samples
- Similarity to known counterfeit clusters
- Image quality scores
- Model version used
- Reference database version used
- Audit trail
```

This is important because the system needs to be explainable enough for business use, dispute handling, model improvement, and legal defensibility.

---

# 2. Recommended Backend Architecture

## 2.1 High-Level Flow

```text
Mobile App / Capture Device
        ↓
API Gateway / Auth
        ↓
Scan Session Service
        ↓
Object Storage for Raw Images
        ↓
Image Intake Queue
        ↓
Image Quality Service
        ↓
Preprocessing / Normalization Service
        ↓
Embedding Inference Service
        ↓
Vector Search / Reference Match Service
        ↓
Scoring & Decision Engine
        ↓
Result / Certificate / Review Queue
```

## 2.2 Main Backend Domains

I would split the backend into four major domains:

| Domain                             | Purpose                                               |
| ---------------------------------- | ----------------------------------------------------- |
| **Operational Platform**           | Users, devices, sessions, uploads, scan status        |
| **Evidence Processing**            | Image validation, normalization, metadata, storage    |
| **ML / Similarity Platform**       | Embeddings, vector search, scoring, anomaly detection |
| **Trust / Review / Certification** | Human review, results, certificates, audit trail      |

This keeps the system clean. The operational system should not know ML internals. The ML system should not own business decisions. The decision engine sits between them.

---

# 3. Core Services

## 3.1 API Gateway / Auth Service

Responsible for:

* User authentication
* Organization/account boundaries
* Device authentication
* Rate limiting
* Upload permissions
* API versioning

For MVP, this can be simple JWT-based auth. Later, if this becomes reseller-facing, you will want:

* Organization accounts
* Role-based access control
* Per-device authorization
* Subscription/usage limits
* Audit logs per authenticated user/device

---

## 3.2 Scan Session Service

This is one of the most important backend services.

A scan should not just be “a pile of photos.” It should be a structured session.

Example:

```json
{
  "scanSessionId": "scan_123",
  "organizationId": "org_001",
  "operatorId": "user_456",
  "deviceId": "device_789",
  "claimedBrand": "Louis Vuitton",
  "claimedCategory": "handbag",
  "claimedMaterial": "monogram_canvas",
  "scanRecipeId": "lv_canvas_handbag_v1",
  "status": "CAPTURING",
  "createdAt": "2026-04-24T21:00:00Z"
}
```

The scan session service manages:

| Responsibility         | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| Session creation       | Start a new authentication attempt                      |
| Scan recipe assignment | Determine which regions must be captured                |
| Upload coordination    | Track expected vs received images                       |
| Status management      | CAPTURING, UPLOADED, PROCESSING, COMPLETE, REVIEW       |
| Idempotency            | Avoid duplicate processing from retrying mobile uploads |
| Auditability           | Preserve who scanned what, when, and with which device  |

---

## 3.3 Scan Recipe Service

This is a key differentiator.

A scan recipe defines what images are required for a given product type.

Example:

```json
{
  "scanRecipeId": "chanel_caviar_flap_v1",
  "brand": "Chanel",
  "category": "handbag",
  "material": "caviar_leather",
  "requiredRegions": [
    {
      "regionCode": "EXTERIOR_LEATHER_GRAIN",
      "minImages": 3,
      "magnificationProfile": "MICRO_200X",
      "lightingProfile": "POLARIZED_RING"
    },
    {
      "regionCode": "STITCHING_EDGE",
      "minImages": 2,
      "magnificationProfile": "MICRO_200X",
      "lightingProfile": "DIFFUSE_RING"
    },
    {
      "regionCode": "HARDWARE_ENGRAVING",
      "minImages": 2,
      "magnificationProfile": "MICRO_100X",
      "lightingProfile": "POLARIZED_RING"
    }
  ]
}
```

The recipe matters because the model should not compare random leather images against random hardware images. It should compare region-specific evidence against region-specific references.

---

## 3.4 Image Upload / Asset Service

Images should be stored as immutable evidence.

For each uploaded image, store:

| Field                 | Purpose                                  |
| --------------------- | ---------------------------------------- |
| `imageAssetId`        | Unique image ID                          |
| `scanSessionId`       | Parent scan                              |
| `regionCode`          | What area this image claims to show      |
| `deviceId`            | Capturing device                         |
| `captureSettings`     | Magnification, exposure, lighting, focus |
| `rawObjectUri`        | Raw file in object storage               |
| `normalizedObjectUri` | Processed version                        |
| `checksum`            | Tamper detection                         |
| `createdAt`           | Evidence timestamp                       |

Do **not** overwrite raw images. Raw captures are evidence.

Recommended storage:

| Data Type         | Storage                                                                    |
| ----------------- | -------------------------------------------------------------------------- |
| Raw images        | S3-compatible object storage                                               |
| Normalized images | S3-compatible object storage                                               |
| Metadata          | PostgreSQL                                                                 |
| Embeddings        | pgvector initially; later Milvus, Weaviate, Pinecone, or OpenSearch vector |
| Event stream      | Kafka, SQS, RabbitMQ, or similar                                           |
| Audit logs        | Append-only table or log store                                             |

Given your background, a strong MVP stack would be:

```text
PostgreSQL + S3-compatible storage + queue + Python inference service
```

Do not overcomplicate the first build with a dozen microservices. Start modular, not distributed.

---

# 4. Image Processing Pipeline

## 4.1 Pipeline Stages

Each uploaded image should go through a deterministic pipeline:

```text
Raw Image
  ↓
Checksum + metadata extraction
  ↓
Image quality scoring
  ↓
Region validation
  ↓
Lens / lighting normalization
  ↓
Crop / resize / color normalization
  ↓
Embedding generation
  ↓
Vector search
  ↓
Region score
```

## 4.2 Image Quality Service

This service prevents garbage-in/garbage-out.

It should score:

| Quality Check               | Reason                                       |
| --------------------------- | -------------------------------------------- |
| Blur / focus                | Microscopic images are useless if soft       |
| Overexposure                | Hardware glare can destroy detail            |
| Underexposure               | Texture disappears                           |
| Glare / specular highlights | Especially important on leather and metal    |
| Motion artifacts            | Handheld device risk                         |
| Field coverage              | Is the region actually visible?              |
| Scale consistency           | Does the image match expected magnification? |
| Color balance               | Avoid lighting/device drift                  |
| Compression artifacts       | Avoid low-quality uploads                    |

Possible outputs:

```json
{
  "imageAssetId": "img_123",
  "qualityStatus": "PASS",
  "sharpnessScore": 0.91,
  "glareScore": 0.12,
  "exposureScore": 0.87,
  "regionConfidence": 0.94,
  "issues": []
}
```

Or:

```json
{
  "qualityStatus": "FAIL",
  "issues": [
    "EXCESSIVE_GLARE",
    "LOW_SHARPNESS"
  ]
}
```

This should happen before expensive ML inference.

---

# 5. ML Inference Backend

## 5.1 Use Multiple Models, Not One Model

A production-grade system should use several model types:

| Model                       | Purpose                                           |
| --------------------------- | ------------------------------------------------- |
| Image quality model         | Is the capture usable?                            |
| Region classifier           | Is this actually stitching/leather/hardware/etc.? |
| Brand/material classifier   | Does the material resemble the claimed class?     |
| Embedding model             | Produces vector representation                    |
| Anomaly detector            | Detects out-of-distribution samples               |
| Decision model/rules engine | Combines evidence into final result               |

The uploaded metric-learning notes make this exact point: metric learning is not a replacement for every classifier; a stronger system combines classifiers, similarity search, anomaly detection, and image-quality checks. 

## 5.2 Embedding Service

This service receives a normalized image and returns a vector.

Example:

```json
{
  "imageAssetId": "img_123",
  "modelVersion": "embedder_leather_v0.3.1",
  "embedding": [0.017, -0.433, 0.221],
  "embeddingDimension": 768
}
```

For MVP, store embeddings in PostgreSQL using pgvector. That keeps infrastructure simple.

Later, if the reference library grows, move to a specialized vector search system.

## 5.3 Vector Search Service

The vector search should be scoped.

Bad query:

```text
Compare this leather image to all images in the database.
```

Good query:

```text
Compare this image to:
- same claimed brand
- same material
- same region type
- same or nearby production era, if known
- authentic and known-counterfeit reference samples
```

Example nearest-neighbor result:

```json
{
  "imageAssetId": "img_123",
  "nearestAuthentic": [
    {
      "referenceId": "ref_001",
      "brand": "Chanel",
      "material": "caviar_leather",
      "region": "EXTERIOR_LEATHER_GRAIN",
      "similarity": 0.94
    }
  ],
  "nearestCounterfeit": [
    {
      "referenceId": "ref_901",
      "similarity": 0.58
    }
  ],
  "authenticClusterScore": 0.91,
  "counterfeitClusterScore": 0.43,
  "outOfDistributionScore": 0.12
}
```

This aligns with your metric-learning concept: the system compares the new image to known authentic and counterfeit samples, rather than simply asking a classifier to emit a brand label. 

---

# 6. Decision Engine

The decision engine should combine region-level evidence.

Example:

```text
Leather grain: strong authentic match
Stitching: moderate authentic match
Hardware engraving: inconclusive due to glare
Heat stamp: strong authentic match
Date code: weak authentic match

Final result: Expert Review Required
```

## 6.1 Decision Inputs

| Input                        | Description                                    |
| ---------------------------- | ---------------------------------------------- |
| Image quality scores         | Are the images usable?                         |
| Region confidence            | Did the user capture the correct areas?        |
| Authentic similarity         | Distance to authentic reference clusters       |
| Counterfeit similarity       | Distance to known counterfeit clusters         |
| OOD score                    | Whether the sample is outside known population |
| Brand/material consistency   | Does evidence match claimed item?              |
| Required-region completeness | Did the scan include enough usable regions?    |
| Model confidence             | Confidence by model version                    |
| Business rules               | Conservative thresholds, review triggers       |

## 6.2 Suggested Result Types

| Result                   | Meaning                                             |
| ------------------------ | --------------------------------------------------- |
| `VERIFIED`               | Strong authentic similarity across required regions |
| `UNVERIFIED`             | Evidence does not support authentication            |
| `INCONCLUSIVE`           | Not enough reliable evidence                        |
| `IMAGE_QUALITY_FAILED`   | User must rescan                                    |
| `EXPERT_REVIEW_REQUIRED` | ML result is ambiguous or high-risk                 |
| `OUT_OF_SCOPE`           | Brand/model/material unsupported                    |

I would avoid returning “FAKE” in the MVP. Use “Unverified” or “Does not support authentication.” That is safer and more professional.

---

# 7. Reference Dataset Backend

This is arguably the most important backend subsystem.

You need to manage known reference samples with chain-of-custody metadata.

## 7.1 Reference Item Model

```json
{
  "referenceItemId": "ref_item_123",
  "authenticityStatus": "CONFIRMED_AUTHENTIC",
  "brand": "Chanel",
  "category": "handbag",
  "model": "Classic Flap",
  "material": "caviar_leather",
  "productionYear": 2021,
  "source": "trusted_reseller_partner",
  "chainOfCustody": "documented",
  "labelConfidence": "HIGH"
}
```

## 7.2 Reference Image Model

```json
{
  "referenceImageId": "ref_img_456",
  "referenceItemId": "ref_item_123",
  "regionCode": "EXTERIOR_LEATHER_GRAIN",
  "deviceProfile": "DINO_LITE_PROFILE_A",
  "lightingProfile": "POLARIZED_RING",
  "objectUri": "s3://reference-images/ref_img_456.tiff",
  "qualityStatus": "PASS",
  "embeddingModelVersion": "embedder_leather_v0.3.1"
}
```

## 7.3 Label Governance

This matters enormously.

The metric-learning notes correctly warn that bad labels or inconsistent capture conditions can ruin the embedding space. The model could accidentally learn “Device A means authentic” instead of learning real material differences. 

So the backend needs label governance:

| Need                   | Implementation                                            |
| ---------------------- | --------------------------------------------------------- |
| Label provenance       | Who labeled this item and why?                            |
| Label confidence       | HIGH / MEDIUM / LOW                                       |
| Label source           | Brand receipt, expert, reseller, known counterfeit source |
| Multi-reviewer support | More than one expert can verify important references      |
| Label history          | Labels should be versioned, not overwritten               |
| Exclusion flags        | Suspect samples can be excluded from training             |

---

# 8. Suggested Data Model

Core tables/entities:

```text
organizations
users
devices
device_calibrations
scan_sessions
scan_recipes
scan_recipe_regions
image_assets
image_quality_reports
normalized_images
embeddings
reference_items
reference_images
reference_labels
model_versions
inference_runs
region_scores
authentication_decisions
review_cases
certificates
audit_events
```

## 8.1 Minimal MVP Tables

For the first backend prototype, you can start with:

| Table                      | Purpose                             |
| -------------------------- | ----------------------------------- |
| `scan_sessions`            | One authentication attempt          |
| `image_assets`             | Uploaded images                     |
| `image_quality_reports`    | Quality results                     |
| `embeddings`               | Vector outputs                      |
| `reference_items`          | Known authentic/counterfeit items   |
| `reference_images`         | Reference image library             |
| `region_scores`            | Per-image/region similarity results |
| `authentication_decisions` | Final result                        |
| `model_versions`           | Model traceability                  |

That is enough to build a real prototype.

---

# 9. API Design

## 9.1 Start Scan Session

```http
POST /v1/scan-sessions
```

Request:

```json
{
  "claimedBrand": "Chanel",
  "claimedCategory": "handbag",
  "claimedModel": "Classic Flap",
  "claimedMaterial": "caviar_leather"
}
```

Response:

```json
{
  "scanSessionId": "scan_123",
  "scanRecipeId": "chanel_caviar_flap_v1",
  "requiredRegions": [
    {
      "regionCode": "EXTERIOR_LEATHER_GRAIN",
      "minImages": 3
    },
    {
      "regionCode": "STITCHING_EDGE",
      "minImages": 2
    },
    {
      "regionCode": "HARDWARE_ENGRAVING",
      "minImages": 2
    }
  ]
}
```

## 9.2 Upload Image

```http
POST /v1/scan-sessions/{scanSessionId}/images
```

Request metadata:

```json
{
  "regionCode": "EXTERIOR_LEATHER_GRAIN",
  "deviceId": "device_789",
  "captureProfile": {
    "magnification": "200x",
    "lighting": "POLARIZED_RING",
    "exposure": "manual",
    "whiteBalance": "fixed"
  }
}
```

Image file is uploaded as multipart or via pre-signed object storage URL.

## 9.3 Submit Scan for Processing

```http
POST /v1/scan-sessions/{scanSessionId}/submit
```

Response:

```json
{
  "scanSessionId": "scan_123",
  "status": "PROCESSING"
}
```

## 9.4 Get Result

```http
GET /v1/scan-sessions/{scanSessionId}/result
```

Response:

```json
{
  "scanSessionId": "scan_123",
  "status": "COMPLETE",
  "result": "EXPERT_REVIEW_REQUIRED",
  "summary": {
    "authenticSimilarity": 0.81,
    "counterfeitSimilarity": 0.47,
    "outOfDistributionScore": 0.32
  },
  "regions": [
    {
      "regionCode": "EXTERIOR_LEATHER_GRAIN",
      "status": "PASS",
      "authenticSimilarity": 0.91,
      "counterfeitSimilarity": 0.41
    },
    {
      "regionCode": "HARDWARE_ENGRAVING",
      "status": "INCONCLUSIVE",
      "reason": "EXCESSIVE_GLARE"
    }
  ]
}
```

---

# 10. Event-Driven Processing

Even in MVP, I would make processing asynchronous.

## 10.1 Events

```text
ScanSessionCreated
ImageUploaded
ImageQualityCompleted
ImageNormalizationCompleted
EmbeddingGenerated
VectorSearchCompleted
RegionScored
AuthenticationDecisionCompleted
ReviewCaseCreated
CertificateIssued
```

## 10.2 Why Async Matters

Image processing and model inference may take time. You do not want mobile clients waiting on long synchronous requests.

The app should submit the scan, poll for status, or receive push notifications.

---

# 11. Recommended MVP Stack

Given your background, I’d separate the backend into a **control plane** and an **ML plane**.

## 11.1 Control Plane

This handles product logic, users, scan sessions, audit, certificates, and review.

Good choices:

```text
Java / Spring Boot
or
Go
```

Given your Java-heavy work and architecture style, Java/Spring Boot would be very natural.

## 11.2 ML Plane

This handles preprocessing, embeddings, model inference, and training.

Use:

```text
Python
FastAPI
PyTorch
OpenCV
Pillow
scikit-image
```

## 11.3 Storage

| Purpose         | MVP Choice                             |
| --------------- | -------------------------------------- |
| Relational data | PostgreSQL                             |
| Vector search   | pgvector                               |
| Raw images      | S3 / MinIO                             |
| Queue           | SQS, RabbitMQ, Kafka, or Redis Streams |
| Model artifacts | S3 / MLflow                            |
| Audit logs      | PostgreSQL append-only table initially |
| Dashboard       | Simple React admin app                 |

## 11.4 MVP Deployment

For local/prototype:

```text
Docker Compose
PostgreSQL + pgvector
MinIO
FastAPI inference service
Spring Boot / Go API service
Redis or RabbitMQ
```

For cloud later:

```text
AWS ECS/EKS
RDS PostgreSQL
S3
SQS/EventBridge
SageMaker or custom GPU inference
CloudFront for certificate pages
```

---

# 12. First Build Slice

The first real slice should be narrow and concrete.

## MVP Slice 1: Ingestion + Evidence Store

Goal:

> Upload microscope images into a structured scan session and preserve evidence.

Deliverables:

* Create scan session
* Upload images
* Store raw image in object storage
* Store metadata in PostgreSQL
* Track required regions
* Display scan session status

No ML yet.

## MVP Slice 2: Image Quality Pipeline

Goal:

> Automatically reject unusable images.

Deliverables:

* Sharpness scoring
* Exposure scoring
* Glare scoring
* Basic region completeness
* Quality report per image

## MVP Slice 3: Embedding Prototype

Goal:

> Generate embeddings and store them.

Deliverables:

* Normalize image
* Run embedding model
* Store vector in pgvector
* Compare to reference vectors

## MVP Slice 4: Region Similarity Scoring

Goal:

> Show nearest authentic and counterfeit reference matches.

Deliverables:

* Per-region nearest-neighbor search
* Authentic similarity score
* Counterfeit similarity score
* OOD score placeholder

## MVP Slice 5: Decision Engine

Goal:

> Produce a conservative scan-level result.

Deliverables:

* Combine region scores
* Apply thresholds
* Return Verified / Unverified / Inconclusive / Review
* Preserve model version and reference version

## MVP Slice 6: Review Console

Goal:

> Let humans inspect ambiguous scans and improve labels.

Deliverables:

* View scan images
* View nearest matches
* Override or confirm result
* Add notes
* Promote images into reference dataset if appropriate

---

# 13. Important Design Warnings

## 13.1 Do Not Build a “Real/Fake” Black Box

A black-box binary result is fragile and legally risky.

Build a system that says:

```text
This evidence strongly matches known authentic references.
```

or:

```text
This evidence does not support authentication.
```

That is safer and more explainable.

## 13.2 Do Not Mix Device Profiles Carelessly

If early authentic samples come from one microscope and counterfeit samples from another, the model may learn device artifacts instead of material truth. Your notes explicitly call out this risk: inconsistent capture conditions can ruin the embedding space. 

Device profile must be first-class metadata.

## 13.3 Do Not Start Too Broad

Do not begin with:

```text
All luxury brands
All handbags
All sneakers
All materials
```

Start with:

```text
One brand
One category
One or two materials
A fixed scan recipe
A fixed imaging profile
```

That gives you a fighting chance of measuring whether the system works.

---

# 14. Strong Initial Architecture Recommendation

For the first serious backend design, I would use this:

```text
Mobile App
  ↓
Spring Boot API Service
  ↓
PostgreSQL + MinIO/S3
  ↓
RabbitMQ or Redis Streams
  ↓
Python FastAPI Image Processing / Inference Worker
  ↓
pgvector Reference Search
  ↓
Spring Boot Decision / Result Service
  ↓
Review Console
```

This gives you:

* Strong backend structure
* Easy ML iteration
* Simple local development
* Clear separation between business logic and ML logic
* A path to cloud deployment later
* Enough architecture to be real, without drowning the MVP in infrastructure

---

# 15. The Backend North Star

The architecture should be built around this principle:

> Every authentication result must be reproducible from stored evidence, model version, reference dataset version, scan recipe, device calibration, and decision rules.

That is the key to making the system trustworthy.

The backend is not just an inference API. It is an **evidence, similarity, decision, and audit platform**.

