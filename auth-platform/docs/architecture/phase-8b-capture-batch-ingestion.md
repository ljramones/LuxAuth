# Phase 8B: Manifest-Based Capture Batch Validation + Ingestion

## Overview

Phase 8B adds a manifest-driven lab capture workflow for ingesting microscope images
in bulk. When microscope images become available (from any source), they can be:

1. **Validated** against a capture protocol
2. **Ingested** into S3 and the reference database
3. **Promoted** to a governed dataset version with train/test splits
4. **Embedded** and **evaluated** using the existing pipeline

## Session Types

| Type | Purpose | Source | Service |
|---|---|---|---|
| Scan session | Authentication pipeline | scan-session-service | Live API |
| Capture session | Device capture intake | capture-intake-service | Live API |
| **Capture batch** | **Lab manifest ingestion** | **scripts** | **Offline** |

## Manifest Format

YAML manifest at `sample_data/lab_captures/{batch_code}/manifest.yaml`:

```yaml
batch_code: lab_lv_monogram_batch_001
source_type: lab_capture
capture_protocol_code: lv_monogram_canvas_handbag_capture
items:
  - external_item_id: lv_auth_001
    authenticity_status: CONFIRMED_AUTHENTIC
    images:
      - region_code: EXTERIOR_CANVAS
        file: lv_auth_001/exterior_canvas_01.png
```

## Workflow

```text
1. Generate/collect images  →  manifest.yaml
2. make validate-capture-batch BATCH=...
3. make ingest-capture-batch BATCH=...
4. make promote-capture-batch BATCH=... DATASET=...
5. make reembed-reference-data MODEL=...
6. make run-evaluation MODEL=...
```

## Validation Checks

- Manifest structure and required fields
- Protocol existence and region codes
- Image file existence and decode
- Image quality metrics
- Duplicate SHA-256 detection
- Region completeness per item
- Label validity

## Split Assignment

Splits are assigned by `external_item_id`, not by image. All images from the same
physical item stay in the same split to prevent data leakage.

Default: 60% train, 20% validation, 20% test

## Leakage Checks

- Same SHA-256 cannot appear across train/test splits
- Same external_item_id cannot span multiple splits
- Perceptual hash duplicates warned if available

## Disclaimers

- Sample lab captures use synthetic images, not real products
- Real microscope images require manual collection and labeling
- This workflow prepares for real data but does not authenticate products
- SageMaker remains deferred
