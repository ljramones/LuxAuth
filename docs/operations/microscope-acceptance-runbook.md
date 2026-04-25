# Microscope Acceptance Runbook

## Purpose

This runbook guides the first real microscope capture session from device setup through
evaluation diagnostics. Follow it step-by-step when a new microscope arrives.

## Prerequisites

- [ ] Auth platform running locally: `make health` all green
- [ ] Synthetic data pipeline verified: `make smoke` passes
- [ ] Capture batch workflow verified: `make smoke-capture-batch` passes
- [ ] Microscope physically connected and producing images (vendor-specific — outside this runbook)
- [ ] USB/network path to transfer images to this machine

## Step 1: Register Device

```bash
curl -X POST http://localhost:8103/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_serial": "DINO-LITE-AM7115MZT-001",
    "device_type": "HANDHELD_MICROSCOPE",
    "organization_id": "a0000000-0000-0000-0000-000000000001",
    "firmware_version": "2.4.1"
  }'
```

Record the returned `device_id`.

## Step 2: Create Calibration Profile

```bash
curl -X POST http://localhost:8103/devices/{device_id}/calibrations \
  -H "Content-Type: application/json" \
  -d '{
    "calibration_profile": {
      "name": "initial_calibration",
      "scale_reference_used": true,
      "white_balance_reference_used": true,
      "magnification": "200x",
      "lighting": "polarized_ring"
    }
  }'
```

Record the returned `calibration_id`.

## Step 3: Capture Non-Brand Test Targets

Before capturing real luxury goods, test with neutral objects:

1. **Plain white card** — verify exposure and white balance
2. **Scale reference** — verify magnification is consistent
3. **Textured fabric sample** — verify focus and sharpness
4. **Metal surface** — verify glare handling

Save these as `test_targets/` — they are for pipeline validation, not authentication.

## Step 4: Repeatability Test

Capture the same region of the same object 5 times without moving the microscope.
Then capture it 5 more times with slight repositioning.

Expected outcome after ingestion:
- Same-position captures should have very high pairwise similarity (>0.95)
- Repositioned captures should still be high (>0.85)
- If not, check focus consistency, lighting stability, and vibration

## Step 5: Create Folder Structure

```text
sample_data/lab_captures/{batch_code}/
  manifest.yaml
  {item_id}/
    exterior_canvas_01.png
    exterior_canvas_02.png
    front_logo_01.png
    interior_stamp_01.png
    hardware_01.png
    stitching_01.png
    stitching_02.png
```

Use the template:
```bash
python3 scripts/create_capture_manifest_template.py \
  --batch-code lab_first_real_batch_001 \
  --device-code DINO-LITE-AM7115MZT-001 \
  --output sample_data/lab_captures/lab_first_real_batch_001/manifest.yaml
```

Edit the manifest to add items and image paths.

## Step 6: Validate

```bash
make validate-capture-batch BATCH=lab_first_real_batch_001
```

Fix any errors before proceeding. Warnings about image quality may indicate capture
technique issues — see the [Capture Quality Guide](capture-quality-guide.md).

## Step 7: Ingest

```bash
make ingest-capture-batch BATCH=lab_first_real_batch_001
```

This uploads raw images to S3, normalizes them, and creates reference records.

## Step 8: Promote to Draft Dataset

```bash
make promote-capture-batch BATCH=lab_first_real_batch_001 DATASET=lab_first_real_v0.1.0
```

Review the split assignment and leakage check output.

## Step 9: Re-Embed with Baseline

```bash
make reembed-reference-data MODEL=texture_baseline_v0.1.0
```

## Step 10: Evaluate

```bash
make run-evaluation MODEL=texture_baseline_v0.1.0
make evaluation-report
```

## Step 11: Run Diagnostics

```bash
make analyze-embeddings MODEL=texture_baseline_v0.1.0
make inspect-neighbors MODEL=texture_baseline_v0.1.0
make calibrate-thresholds MODEL=texture_baseline_v0.1.0
make export-projection MODEL=texture_baseline_v0.1.0
```

## Pass/Fail Criteria

| Check | Pass | Investigate |
|---|---|---|
| All images decode | Yes | Check file format, capture software settings |
| Image quality PASS rate | >80% | Check focus, lighting, glare |
| Repeatability similarity | >0.85 same object | Check stability, focus consistency |
| Authentic cluster separation | Positive score | Check label correctness, capture consistency |
| NN label agreement | >70% | May need more samples or better capture protocol |

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| All images fail quality | Wrong format or too dark | Check microscope output settings |
| Low sharpness scores | Out of focus | Adjust working distance, use fixed focus |
| High glare scores | Specular reflection | Add polarizer or diffuser |
| No cluster separation | Too few samples or bad labels | Capture more items, verify labels |
| Validation errors | Wrong region codes | Check manifest against protocol |

## Do Not

- Do NOT capture images of items you do not own or have permission to image
- Do NOT use brand logos as test targets
- Do NOT claim authentication results from this local system
- Do NOT upload real customer items without proper chain-of-custody documentation
- Do NOT skip the calibration step
- Do NOT overwrite raw images — they are immutable evidence
