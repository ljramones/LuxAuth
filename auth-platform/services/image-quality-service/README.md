# Image Quality Service

## Purpose

Assesses uploaded evidence images for technical quality using OpenCV computer vision metrics. Acts as the first gate in the authentication pipeline, rejecting images that are too blurry, poorly exposed, glare-heavy, or too small to produce reliable downstream results.

## Responsibilities

- Download raw evidence images from S3.
- Compute sharpness, exposure, and glare scores via `compute_quality_metrics()`.
- Classify each image as `PASS` or `FAIL`.
- Persist a detailed quality report to `image_quality_reports`.
- Publish passing images to the normalization queue for the next pipeline stage.

## Non-Responsibilities

- Does not resize, crop, or otherwise transform images (see normalization-service).
- Does not authenticate items; quality assessment is purely technical.
- Does not manage image upload or metadata creation (see evidence-asset-service / capture-intake-service).

## Runtime

| Property | Value |
|---|---|
| Port | `8201` |
| Healthcheck | `GET /health` |
| Readiness | `GET /ready` |
| Worker queue | `image-quality-queue` |
| Framework | FastAPI |

## Main APIs

### POST /process/{image_asset_id}

Trigger quality assessment for a single image asset.

**Request**

```
POST /process/01J7X9K2M3N4P5Q6R7S8T9U0
```

**Response 200 (pass)**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "quality_status": "PASS",
  "sharpness_score": 0.82,
  "exposure_score": 0.91,
  "glare_score": 0.05,
  "issues": []
}
```

**Response 200 (fail)**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "quality_status": "FAIL",
  "sharpness_score": 0.18,
  "exposure_score": 0.45,
  "glare_score": 0.62,
  "issues": ["LOW_SHARPNESS", "UNDEREXPOSED", "EXCESSIVE_GLARE"]
}
```

### GET /reports/{image_asset_id}

Retrieve a previously computed quality report.

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "quality_status": "PASS",
  "sharpness_score": 0.82,
  "exposure_score": 0.91,
  "glare_score": 0.05,
  "issues": [],
  "created_at": "2026-04-24T10:15:30Z"
}
```

### GET /health

Returns `{"status": "ok"}` when the process is alive.

### GET /ready

Returns 200 when the service can reach the database and SQS.

## Quality Metrics

| Metric | Method | Range | Failure Issue |
|---|---|---|---|
| `sharpness_score` | Laplacian variance, normalized 0-1 | 0.0 -- 1.0 | `LOW_SHARPNESS` |
| `exposure_score` | Luminance histogram analysis, peak at 128 | 0.0 -- 1.0 | `UNDEREXPOSED` / `OVEREXPOSED` |
| `glare_score` | Ratio of bright + low-saturation pixels | 0.0 -- 1.0 | `EXCESSIVE_GLARE` |

Additional issue codes:

- `DECODE_FAILED` -- image bytes could not be decoded by OpenCV.
- `IMAGE_TOO_SMALL` -- image dimensions fall below the minimum threshold.

`quality_status` is `PASS` when no issues are detected, `FAIL` otherwise.

## Events Consumed

| Event | Queue | Description |
|---|---|---|
| `IMAGE_UPLOADED` | `image-quality-queue` | Triggers quality assessment for a newly uploaded image. |

## Events Published

| Event | Queue | Condition |
|---|---|---|
| `IMAGE_QUALITY_COMPLETED` | `normalization-queue` | Published only when `quality_status` is `PASS`. |

On `FAIL`, the pipeline halts for that image. The failure is logged and persisted but no downstream event is emitted.

## Database Tables

| Table | Access | Purpose |
|---|---|---|
| `image_assets` | Read | Look up image metadata and S3 key. |
| `image_quality_reports` | Write | Persist quality scores and issue list. |
| `processing_runs` | Read/Write | Idempotency tracking. |

## S3 Usage

| Bucket | Access | Purpose |
|---|---|---|
| `auth-platform-raw-evidence` | Read | Download the original uploaded image for analysis. |

## Configuration

| Setting | Description |
|---|---|
| `sqs_quality_queue` | SQS queue URL for incoming quality assessment requests. |
| `sqs_normalization_queue` | SQS queue URL for publishing passing images downstream. |
| `s3_raw_bucket` | S3 bucket name for raw evidence images. |
| `consume_queue` | Queue name the worker polls. |

## Local Development

```bash
cd services/image-quality-service

# Install dependencies (requires OpenCV)
pip install -e ".[dev]"

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8201 --reload

# Run the worker
python -m app.worker
```

Requires a running PostgreSQL instance and LocalStack (or real AWS) for SQS and S3.

## Observability

- Structured logs include `image_asset_id`, `quality_status`, and individual metric scores on every assessment.
- Audit event `IMAGE_QUALITY_COMPLETED` is recorded for all passing images.
- Failed assessments are logged at WARN level with the full issue list.

## Idempotency

Key format: `{image_id}|IMAGE_QUALITY|stub_quality_v0.1.0`

Duplicate processing is prevented via the `processing_runs` table. If a run with the same idempotency key already exists, the handler returns the existing result without reprocessing.

## Security Notes

- Reads raw user-uploaded bytes. OpenCV decode failures are caught and surfaced as `DECODE_FAILED` rather than propagated as exceptions.
- No image data is returned through the API -- only numeric scores and status codes.
- S3 access uses IAM role credentials; no keys are stored in application config.

## Current Limitations

- Quality thresholds are hardcoded; there is no per-brand or per-item-type tuning.
- The `stub_quality_v0.1.0` version identifier indicates this is an initial implementation. Metric weights and thresholds are expected to evolve.
- No GPU acceleration; all OpenCV operations run on CPU.

## Related Documentation

- [Normalization Service](../normalization-service/README.md) -- next pipeline stage after quality pass.
- [Evidence Asset Service](../evidence-asset-service/README.md) -- manages image upload and metadata.
- [Capture Intake Service](../capture-intake-service/README.md) -- orchestrates initial image capture flow.
