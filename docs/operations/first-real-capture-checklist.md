# First Real Capture Checklist

Quick reference for the first microscope capture session.
See the [Microscope Acceptance Runbook](microscope-acceptance-runbook.md) for details.

## Before Capturing

- [ ] `make health` — all 13 services green
- [ ] `make smoke` — existing pipeline works
- [ ] `make smoke-capture-batch` — batch workflow works
- [ ] Microscope connected and producing images
- [ ] Scale reference and white balance reference available

## Device Setup

- [ ] Register device: `POST /devices/register`
- [ ] Create calibration: `POST /devices/{id}/calibrations`
- [ ] Record device_id and calibration_id

## Test Captures (Non-Brand)

- [ ] Plain white card — check exposure
- [ ] Scale reference — check magnification
- [ ] Textured fabric — check sharpness
- [ ] Metal surface — check glare handling
- [ ] Validate test images: check quality scores

## Repeatability Test

- [ ] Same object, same position, 5 captures
- [ ] Same object, repositioned, 5 captures
- [ ] Verify similarity >0.85

## Real Capture

- [ ] Create batch directory and manifest (use template script)
- [ ] Capture all required regions per item
- [ ] Multiple images per region where protocol requires
- [ ] `make validate-capture-batch BATCH=...`
- [ ] Fix any errors
- [ ] `make ingest-capture-batch BATCH=...`
- [ ] `make promote-capture-batch BATCH=... DATASET=...`

## Diagnostics

- [ ] `make analyze-embeddings MODEL=texture_baseline_v0.1.0`
- [ ] `make inspect-neighbors MODEL=texture_baseline_v0.1.0`
- [ ] `make run-evaluation MODEL=texture_baseline_v0.1.0`
- [ ] `make evaluation-report`
- [ ] Review cluster separation and NN agreement

## Done

- [ ] Raw images stored in S3
- [ ] Normalized PNGs generated
- [ ] Embeddings computed
- [ ] Dataset version created (draft)
- [ ] Evaluation metrics recorded
