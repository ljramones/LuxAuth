# Normalization Service

## Purpose

Creates standardized image derivatives from raw evidence. Every image that passes quality assessment is EXIF-corrected, converted to RGB, center-cropped to a square, resized to 512x512 pixels, and output as PNG. This ensures all downstream models receive consistent input regardless of the original capture device or orientation.

## Responsibilities

- Download raw evidence images from S3.
- Apply `normalize_image()`: EXIF orientation fix, RGB conversion, center-crop to square, resize to 512x512, output as PNG.
- Upload the normalized PNG to S3 with a deterministic key.
- Record the normalization result in the `normalized_images` table.
- Publish an event to advance the image to the embedding stage.

## Non-Responsibilities

- Does not assess image quality (see image-quality-service).
- Does not generate embeddings or perform any ML inference (see embedding-service).
- Does not decide authentication outcomes.

## Runtime

| Property | Value |
|---|---|
| Port | `8202` |
| Healthcheck | `GET /health` |
| Readiness | `GET /ready` |
| Worker queue | `normalization-queue` |
| Framework | FastAPI |

## Main APIs

### POST /process/{image_asset_id}

Trigger normalization for a single image asset.

**Request**

```
POST /process/01J7X9K2M3N4P5Q6R7S8T9U0
```

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "normalized_s3_key": "sess_abc123/01J7X9K2M3N4P5Q6R7S8T9U0_normalized.png",
  "preprocessing_version": "normalize_image_v0.1.0",
  "width": 512,
  "height": 512,
  "format": "PNG"
}
```

### GET /results/{image_asset_id}

Retrieve a previously stored normalization result.

**Response 200**

```json
{
  "image_asset_id": "01J7X9K2M3N4P5Q6R7S8T9U0",
  "normalized_s3_key": "sess_abc123/01J7X9K2M3N4P5Q6R7S8T9U0_normalized.png",
  "preprocessing_version": "normalize_image_v0.1.0",
  "created_at": "2026-04-24T10:16:00Z"
}
```

### GET /health

Returns `{"status": "ok"}` when the process is alive.

### GET /ready

Returns 200 when the service can reach the database, SQS, and S3.

## Normalization Pipeline

The `normalize_image()` function applies the following steps in order:

1. **EXIF orientation fix** -- rotates/flips the image according to its EXIF orientation tag so the image is upright regardless of how the camera stored it.
2. **RGB conversion** -- converts RGBA, grayscale, or other color modes to standard RGB.
3. **Center-crop to square** -- crops from the center using the shorter dimension as the side length.
4. **Resize to 512x512** -- bicubic downscale (or upscale) to the standard input size.
5. **Output as PNG** -- lossless encoding to preserve detail for embedding generation.

Preprocessing version: `normalize_image_v0.1.0`

## Events Consumed

| Event | Queue | Description |
|---|---|---|
| `IMAGE_QUALITY_COMPLETED` | `normalization-queue` | Triggers normalization for an image that passed quality checks. |

## Events Published

| Event | Queue | Description |
|---|---|---|
| `IMAGE_NORMALIZED` | `embedding-queue` | Published after successful normalization and S3 upload. |

## Database Tables

| Table | Access | Purpose |
|---|---|---|
| `image_assets` | Read | Look up image metadata and S3 key for the raw image. |
| `normalized_images` | Write | Record the normalized image S3 key, preprocessing version, and dimensions. |
| `processing_runs` | Read/Write | Idempotency tracking. |

## S3 Usage

| Bucket | Access | Purpose |
|---|---|---|
| `auth-platform-raw-evidence` | Read | Download the original uploaded image. |
| `auth-platform-normalized-evidence` | Write | Upload the normalized PNG. Key format: `{scan_session_id}/{image_asset_id}_normalized.png`. |

## Configuration

| Setting | Description |
|---|---|
| `sqs_normalization_queue` | SQS queue URL for incoming normalization requests. |
| `sqs_embedding_queue` | SQS queue URL for publishing normalized images downstream. |
| `s3_raw_bucket` | S3 bucket name for raw evidence images. |
| `s3_normalized_bucket` | S3 bucket name for normalized output images. |

## Local Development

```bash
cd services/normalization-service

pip install -e ".[dev]"

# Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8202 --reload

# Run the worker
python -m app.worker
```

Requires PostgreSQL, and LocalStack (or real AWS) for SQS and S3.

## Observability

- Structured logs include `image_asset_id`, `normalized_s3_key`, and `preprocessing_version`.
- Audit event `IMAGE_NORMALIZED` is recorded for every successful normalization.

## Idempotency

Key format: `{image_id}|NORMALIZATION|normalize_stub_v0.1.0`

Duplicate processing is prevented via the `processing_runs` table. Re-delivery of the same SQS message produces no side effects.

## Security Notes

- Raw image bytes are downloaded, transformed in memory, and uploaded. No image data is persisted to local disk.
- S3 access uses IAM role credentials.
- The normalized output bucket is separate from the raw bucket to enable distinct access policies.

## Current Limitations

- Output size is fixed at 512x512; there is no per-model or per-region size configuration.
- Only PNG output is supported. Future versions may support WebP or other formats.
- `normalize_image_v0.1.0` is the initial implementation; the preprocessing version is tracked so downstream consumers can distinguish results from future versions.

## Related Documentation

- [Image Quality Service](../image-quality-service/README.md) -- preceding pipeline stage.
- [Embedding Service](../embedding-service/README.md) -- next pipeline stage after normalization.
