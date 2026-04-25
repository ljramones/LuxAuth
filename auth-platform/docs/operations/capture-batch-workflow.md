# Capture Batch Workflow

## Quick Start

```bash
# Generate sample batch (synthetic images)
make generate-lab-capture-batch

# Validate manifest and images
make validate-capture-batch BATCH=lab_lv_monogram_batch_001

# Ingest to S3 and reference database
make ingest-capture-batch BATCH=lab_lv_monogram_batch_001

# Promote to a draft dataset
make promote-capture-batch BATCH=lab_lv_monogram_batch_001 DATASET=lab_lv_monogram_v0.1.0

# Embed references and evaluate
make reembed-reference-data DATASET=lab_lv_monogram_v0.1.0 MODEL=texture_baseline_v0.1.0
make run-evaluation
```

## Status Lifecycle

```text
CREATED → VALIDATING → VALIDATED / VALIDATED_WITH_WARNINGS / FAILED
VALIDATED → INGESTED
INGESTED → PROMOTED
```

## Adding Real Microscope Images

1. Create a directory: `sample_data/lab_captures/{batch_code}/`
2. Place images in subdirectories by item: `{external_item_id}/{region}_{index}.{ext}`
3. Write `manifest.yaml` following the format in phase-8b docs
4. Run validate → ingest → promote
