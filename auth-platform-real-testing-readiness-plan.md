# Auth Platform — Real Testing Readiness Plan

**Document purpose:** Define how we proceed from synthetic/local validation into real microscope image testing, and prepare the platform to accept those images once a microscope is available.

**Current state:** The platform has a working local microservice stack, event-driven image pipeline, real image validation, baseline texture embeddings, local metric-learning lifecycle, dataset governance, evaluation harness, and ML diagnostics. The next milestone should not be further synthetic tuning. The next milestone is preparing the system to ingest real capture batches correctly, safely, and reproducibly.

**Important constraint:** We do not yet have the microscope. This phase therefore prepares the backend, data contracts, manifests, validation scripts, and dataset-promotion workflow so that when microscope images arrive, they can be ingested without redesigning the platform.

---

## 1. Executive Summary

The system is now ready to move from synthetic validation to **real capture readiness**.

The immediate objective is not to authenticate products. The objective is to prepare for controlled real-world testing by making the platform able to accept microscope image batches with strict metadata:

- device identity
- calibration profile
- capture protocol
- item identity
- region code
- authenticity label
- label provenance
- image quality results
- split assignment
- leakage checks
- dataset versioning
- model/evaluation reproducibility

Once microscope images exist, they should enter the system through a disciplined **capture batch workflow**, not through ad hoc image uploads.

The desired flow is:

```text
Microscope capture folder
  ↓
Manifest file
  ↓
Capture batch validation
  ↓
Image quality + checksum + duplicate checks
  ↓
Controlled ingestion into S3/Postgres
  ↓
Promotion into a governed dataset version
  ↓
Re-embedding
  ↓
Evaluation
  ↓
Diagnostics and model comparison
```

---

## 2. Why We Should Stop Tuning on Synthetic Images

Synthetic data has already done its job. It proved:

- the local pipeline runs end-to-end
- image validation works
- normalization works
- baseline embeddings work
- pgvector search works
- model version filtering works
- evaluation and diagnostics work
- local metric-learning lifecycle works

The learned model currently underperforms the baseline on synthetic data, but that is expected. Synthetic textures are too simple and too separable by hand-crafted histogram features. Real microscope images will introduce the actual problem:

- subtle material variation
- glare
- uneven focus
- stitching variation
- hardware reflections
- manufacturing batch variation
- real counterfeit variation
- operator variation
- device calibration drift
- region-capture ambiguity

Further tuning on synthetic data risks optimizing for the wrong problem.

---

## 3. Real Testing Goals

Real testing should answer these questions in order:

### 3.1 Capture Quality

Can the microscope produce repeatable, usable images?

We need to measure:

- sharpness
- exposure
- glare
- resolution
- field coverage
- region consistency
- repeatability across captures
- repeatability across sessions

### 3.2 Pipeline Compatibility

Can the current platform accept real microscope images without special handling?

We need to validate:

- upload/ingestion works
- image validation accepts microscope outputs
- normalization produces stable 512×512 PNG derivatives
- embeddings are generated
- vector search operates on real reference images
- evaluation harness works against a real capture dataset

### 3.3 Dataset Quality

Can we build a governed dataset from real images?

We need to track:

- item provenance
- authenticity label confidence
- duplicate images
- duplicate physical items
- region completeness
- train/validation/test leakage
- source-device consistency
- device calibration metadata

### 3.4 Model Readiness

Do the baseline and learned embeddings show any meaningful separation on real captures?

We need diagnostics for:

- cluster separation
- nearest-neighbor label agreement
- authentic-authentic similarity
- counterfeit-counterfeit similarity
- authentic-counterfeit similarity
- region-by-region performance
- threshold sensitivity
- false positives
- false negatives
- expert-review rate

---

## 4. Near-Term Plan Before the Microscope Arrives

Since the microscope is not available yet, the next engineering phase should focus on **acceptance readiness**.

This means building the structures that will allow real images to be accepted safely.

### Phase 8A — Capture Protocol and Manifest Preparation

Create the capture protocol model and manifest format.

Deliverables:

- `capture_protocols` table
- `capture_protocol_regions` table
- default active capture protocol for Louis Vuitton monogram canvas handbag testing
- YAML manifest schema
- manifest parser
- manifest validation script
- documentation

### Phase 8B — Capture Batch Validation

Create validation tooling that can inspect a folder of image files before they become reference data.

Deliverables:

- `capture_batches` table
- `capture_batch_items` table
- `capture_batch_images` table
- `capture_batch_validation_reports` table
- `scripts/validate_capture_batch.py`
- duplicate SHA-256 detection
- perceptual duplicate warning, if supported
- required-region completeness checks
- label validation
- image quality checks
- validation report output

### Phase 8C — Capture Batch Ingestion

Create controlled ingestion from a validated folder into the platform.

Deliverables:

- `scripts/ingest_capture_batch.py`
- raw image upload to S3/LocalStack
- normalized image creation
- candidate reference item creation
- candidate reference image creation
- label review creation
- audit events

### Phase 8D — Dataset Promotion

Create a safe promotion flow from ingested capture batch to a governed dataset version.

Deliverables:

- `scripts/promote_capture_batch_to_dataset.py`
- deterministic train/validation/test split assignment
- leakage checks
- no automatic activation unless explicitly requested
- audit events
- dataset promotion documentation

### Phase 8E — Real Image Evaluation Path

Ensure the existing evaluation and diagnostic tools can run against a promoted real-image dataset.

Deliverables:

- `make reembed-reference-data DATASET=... MODEL=...`
- `make run-evaluation DATASET=... MODEL=...`
- `make analyze-embeddings DATASET=... MODEL=...`
- `make inspect-neighbors DATASET=... MODEL=...`
- `make calibrate-thresholds DATASET=... MODEL=...`
- `make export-projection DATASET=... MODEL=...`

---

## 5. Capture Protocol vs Scan Recipe

The system should distinguish between two related but different concepts.

| Concept | Purpose | Used By |
|---|---|---|
| Scan recipe | Defines what an operator must capture during an authentication scan | Mobile/app-facing authentication flow |
| Capture protocol | Defines how lab/reference data must be collected for dataset construction | Lab ingestion and dataset governance |

For example:

```text
scan_recipe:
  lv_monogram_canvas_handbag_v1

capture_protocol:
  lv_monogram_canvas_handbag_capture:v0.1.0
```

They may use the same region codes, but they are not the same artifact.

The scan recipe is customer/workflow oriented.

The capture protocol is research/data-quality oriented.

---

## 6. Initial Capture Protocol

Use this as the first real-testing capture protocol.

```yaml
protocol_code: lv_monogram_canvas_handbag_capture
protocol_version: v0.1.0
brand: Louis Vuitton
category: handbag
material: monogram_canvas
status: active

regions:
  - region_code: EXTERIOR_CANVAS
    min_images: 3
    required: true
    notes: Capture multiple areas of exterior coated canvas away from obvious damage.

  - region_code: FRONT_LOGO_PRINT
    min_images: 2
    required: true
    notes: Capture printed logo/pattern area with minimal glare.

  - region_code: INTERIOR_HEAT_STAMP
    min_images: 2
    required: true
    notes: Capture stamp edge, impression depth, and surrounding material.

  - region_code: HARDWARE_ENGRAVING
    min_images: 2
    required: true
    notes: Capture engraving and adjacent metal finish. Glare control is critical.

  - region_code: STITCHING_DETAIL
    min_images: 3
    required: true
    notes: Capture thread texture, stitch holes, and material around the stitch line.
```

The `min_images` values are intentionally higher than the current smoke-test recipe. Real testing needs repeatability and multiple samples per region.

---

## 7. Real Capture Folder Structure

When the microscope arrives, organize image captures like this:

```text
sample_data/lab_captures/
  lab_lv_monogram_batch_001/
    manifest.yaml
    lv_auth_001/
      exterior_canvas_01.png
      exterior_canvas_02.png
      exterior_canvas_03.png
      front_logo_01.png
      front_logo_02.png
      interior_stamp_01.png
      interior_stamp_02.png
      hardware_01.png
      hardware_02.png
      stitching_01.png
      stitching_02.png
      stitching_03.png

    lv_auth_002/
      ...

    lv_fake_001/
      ...

    lv_fake_002/
      ...
```

Do not mix casual test images with reference-candidate captures.

Each batch should have one manifest and one clear purpose.

---

## 8. Manifest Format

Each capture batch should have a `manifest.yaml`.

Example:

```yaml
batch_code: lab_lv_monogram_batch_001
source_type: lab_capture
capture_protocol_code: lv_monogram_canvas_handbag_capture
capture_protocol_version: v0.1.0
device_id: local_dev_microscope_001
calibration_profile: local_dev_calibration_v0.1.0
operator: larry
notes: Initial microscope acceptance batch for pipeline validation.

items:
  - external_item_id: lv_auth_001
    brand: Louis Vuitton
    category: handbag
    material: monogram_canvas
    model: null
    production_year: null
    authenticity_status: CONFIRMED_AUTHENTIC
    label_confidence: high
    provenance_type: lab_curated
    notes: Known authentic test item.
    images:
      - region_code: EXTERIOR_CANVAS
        file: lv_auth_001/exterior_canvas_01.png
      - region_code: EXTERIOR_CANVAS
        file: lv_auth_001/exterior_canvas_02.png
      - region_code: EXTERIOR_CANVAS
        file: lv_auth_001/exterior_canvas_03.png
      - region_code: FRONT_LOGO_PRINT
        file: lv_auth_001/front_logo_01.png
      - region_code: INTERIOR_HEAT_STAMP
        file: lv_auth_001/interior_stamp_01.png
      - region_code: HARDWARE_ENGRAVING
        file: lv_auth_001/hardware_01.png
      - region_code: STITCHING_DETAIL
        file: lv_auth_001/stitching_01.png

  - external_item_id: lv_fake_001
    brand: Louis Vuitton
    category: handbag
    material: monogram_canvas
    model: null
    production_year: null
    authenticity_status: CONFIRMED_COUNTERFEIT
    label_confidence: high
    provenance_type: lab_curated
    notes: Known counterfeit test item.
    images:
      - region_code: EXTERIOR_CANVAS
        file: lv_fake_001/exterior_canvas_01.png
      - region_code: FRONT_LOGO_PRINT
        file: lv_fake_001/front_logo_01.png
      - region_code: INTERIOR_HEAT_STAMP
        file: lv_fake_001/interior_stamp_01.png
      - region_code: HARDWARE_ENGRAVING
        file: lv_fake_001/hardware_01.png
      - region_code: STITCHING_DETAIL
        file: lv_fake_001/stitching_01.png
```

---

## 9. Device and Calibration Metadata

The device must be treated as part of the dataset.

When the microscope arrives, register:

```yaml
device_id: local_dev_microscope_001
device_type: digital_microscope
manufacturer: unknown_or_vendor_name
model: unknown_or_model_name
connection_type: usb_or_wifi
magnification_profile: to_be_measured
lighting_profile: integrated_led
calibration_profile: local_dev_calibration_v0.1.0
```

Calibration metadata should include:

```yaml
calibration_profile: local_dev_calibration_v0.1.0
calibration_date: YYYY-MM-DD
operator: larry
scale_reference_used: true_or_false
white_balance_reference_used: true_or_false
notes: Initial local calibration profile.
```

Even if early values are approximate, the platform should store them.

---

## 10. First Microscope Acceptance Test

When the microscope arrives, do not start with luxury goods.

Start with controlled image-quality targets.

### 10.1 Target Set A — Basic Imaging

Capture:

- plain white paper
- black printed text
- woven fabric
- leather-like material
- coin or machined metal
- printed packaging
- stitching on ordinary cloth

Purpose:

- verify decoding
- verify sharpness scoring
- verify glare scoring
- verify exposure scoring
- verify normalization
- verify that the microscope image format is accepted

### 10.2 Target Set B — Repeatability

Capture the same region 10 times without moving the target.

Then capture the same region 10 times after lifting and repositioning the microscope each time.

Measure:

- embedding similarity within same fixed capture
- embedding similarity after repositioning
- sharpness variance
- exposure variance
- glare variance

This tells us whether the capture device/procedure is stable enough for ML.

### 10.3 Target Set C — Region Simulation

Use non-brand materials to simulate the future item regions:

| Simulated Region | Test Material |
|---|---|
| EXTERIOR_CANVAS | textured coated fabric or printed canvas |
| FRONT_LOGO_PRINT | printed paper or packaging |
| INTERIOR_HEAT_STAMP | embossed leather-like material if available |
| HARDWARE_ENGRAVING | coin, key, or engraved metal |
| STITCHING_DETAIL | stitched fabric or leather scrap |

Purpose:

- validate region capture workflow
- validate manifest structure
- validate batch ingestion before using actual reference items

---

## 11. First Real Item Testing

Only after microscope acceptance testing should we capture real target-category items.

### 11.1 Minimum First Batch

Minimum useful batch:

```text
2 known authentic items
2 known counterfeit items
5 required regions per item
2–3 images per region
```

That gives approximately:

```text
4 items × 5 regions × 2–3 images = 40–60 images
```

This is not enough for a strong model, but enough to validate ingestion, quality, diagnostics, and evaluation behavior.

### 11.2 Better First Batch

Better initial lab batch:

```text
5 known authentic items
5 known counterfeit items
5 required regions per item
3 images per region
```

Approximately:

```text
10 items × 5 regions × 3 images = 150 images
```

This is enough to start seeing whether baseline texture features or learned embeddings show any meaningful signal.

### 11.3 First Serious Dataset

A more meaningful early dataset:

```text
25 authentic items
25 counterfeit items
5 regions per item
3 images per region
```

Approximately:

```text
50 items × 5 regions × 3 images = 750 images
```

This still is not commercial-grade, but it becomes useful for measuring whether the approach has traction.

---

## 12. Validation Gates Before Dataset Promotion

A capture batch should not become a dataset version unless it passes these gates.

### 12.1 Fatal Validation Failures

Reject or quarantine the batch if:

- manifest cannot be parsed
- capture protocol is missing
- invalid region codes are used
- required images are missing for most items
- image files cannot be decoded
- labels are missing
- authenticity status is invalid
- duplicate SHA-256 images appear across different items
- same physical item would be split across train/test

### 12.2 Warning Conditions

Allow validation with warnings if:

- individual images fail quality checks
- glare is high on hardware
- sharpness is borderline
- an item has optional-region gaps
- perceptual duplicates appear within the same item/region
- calibration profile is incomplete
- microscope model metadata is incomplete

Warnings should be visible in the validation report.

---

## 13. Dataset Promotion Rules

When promoting a capture batch into a dataset version:

- create a new dataset version
- default status should be `draft`
- never automatically activate it
- assign splits by physical item, not image
- keep all images from one item in one split
- prevent duplicate checksums across splits
- warn on perceptual duplicates across splits
- record the capture protocol version
- record device and calibration profile
- write audit events

Example command:

```bash
make promote-capture-batch \
  BATCH=lab_lv_monogram_batch_001 \
  DATASET=lab_lv_monogram_v0.1.0
```

Activation should be explicit:

```bash
make activate-dataset DATASET=lab_lv_monogram_v0.1.0
```

---

## 14. Evaluation Path for Real Captures

Once a lab dataset exists:

```bash
make reembed-reference-data \
  DATASET=lab_lv_monogram_v0.1.0 \
  MODEL=texture_baseline_v0.1.0

make run-evaluation \
  DATASET=lab_lv_monogram_v0.1.0 \
  MODEL=texture_baseline_v0.1.0

make evaluation-report

make analyze-embeddings \
  DATASET=lab_lv_monogram_v0.1.0 \
  MODEL=texture_baseline_v0.1.0

make inspect-neighbors \
  DATASET=lab_lv_monogram_v0.1.0 \
  MODEL=texture_baseline_v0.1.0
```

Do the same for learned models only after the baseline is understood.

---

## 15. Expected First Real Results

The first real results will probably be messy.

Expected issues:

- many hardware images may fail glare checks
- region images may be inconsistent
- the baseline may not separate authentic/counterfeit well
- learned embeddings may remain weak until the dataset grows
- some item labels may be less certain than expected
- quality thresholds may need adjustment
- capture protocol may need region-specific guidance

This is not a problem. The goal of the first real run is to expose those issues.

---

## 16. Implementation Tasks to Prepare Now

### 16.1 Schema

Add:

- `capture_protocols`
- `capture_protocol_regions`
- `capture_batches`
- `capture_batch_items`
- `capture_batch_images`
- `capture_batch_validation_reports`

### 16.2 Scripts

Add:

- `scripts/validate_capture_batch.py`
- `scripts/ingest_capture_batch.py`
- `scripts/promote_capture_batch_to_dataset.py`
- optional `scripts/create_capture_manifest_template.py`
- optional `scripts/register_local_microscope.py`

### 16.3 Makefile Commands

Add:

```bash
make create-capture-manifest-template BATCH=...
make validate-capture-batch BATCH=...
make ingest-capture-batch BATCH=...
make promote-capture-batch BATCH=... DATASET=...
make reembed-reference-data DATASET=... MODEL=...
make run-evaluation DATASET=... MODEL=...
```

### 16.4 Documentation

Add:

- `docs/architecture/phase-8-real-capture-protocol-lab-ingestion.md`
- `docs/capture-protocols/lv-monogram-canvas-handbag-v0.1.0.md`
- `docs/operations/microscope-acceptance-test.md`
- `docs/operations/capture-batch-manifest.md`

---

## 17. Acceptance Criteria for the Readiness Phase

The project is ready for microscope images when:

1. `make health` passes.
2. Existing smoke tests still pass.
3. Existing synthetic evaluation still passes.
4. A sample lab capture manifest can be validated.
5. Capture batch validation creates a validation report.
6. Capture batch ingestion uploads raw and normalized images.
7. Capture batch promotion creates a draft dataset version.
8. Leakage checks run during promotion.
9. Dataset activation is explicit.
10. Real image datasets can be re-embedded and evaluated by dataset version.
11. Audit events exist for capture batch lifecycle actions.
12. No SageMaker is required.
13. No production authentication claims are made.

---

## 18. First Day With the Microscope Checklist

When the microscope arrives:

1. Register the device.
2. Create a local calibration profile.
3. Capture non-brand test targets.
4. Validate image format, decode, size, and quality metrics.
5. Run repeatability captures.
6. Create a sample manifest.
7. Validate the capture batch.
8. Ingest the capture batch.
9. Promote to a draft dataset.
10. Re-embed with `texture_baseline_v0.1.0`.
11. Run evaluation.
12. Run embedding diagnostics.
13. Inspect nearest neighbors.
14. Adjust capture protocol before capturing more items.

---

## 19. Do Not Do Yet

Do not:

- claim authentication performance
- use results commercially
- tune thresholds to hide bad results
- mix microscope images with synthetic images in the same dataset version
- mix device profiles without recording them
- split images from the same physical item across train/test
- activate a real dataset automatically
- introduce SageMaker before local real-data behavior is understood
- optimize the learned model before capture quality and dataset quality are known

---

## 20. Recommended Next Engineering Prompt

Use this prompt with Claude Code to implement the readiness work.

```text
We have completed the local Auth Platform pipeline through Phase 7:
- queue-driven evidence pipeline
- real image validation and normalization
- texture_baseline_v0.1.0 embeddings
- local metric-learning lifecycle
- dataset governance
- evaluation harness
- ML diagnostics and calibration tools

We do not yet have a microscope, so do not implement assumptions tied to a specific device vendor.

Implement Phase 8A/8B: Real Capture Readiness.

Do not add SageMaker.
Do not add Kubernetes.
Do not add Terraform.
Do not claim real authentication capability.
Do not break existing smoke tests.
Do not remove existing synthetic-data tools.

Goals:
1. Add capture protocol tables.
2. Add capture batch tables.
3. Add default active capture protocol:
   lv_monogram_canvas_handbag_capture:v0.1.0
4. Add YAML manifest parser for lab capture batches.
5. Add scripts/validate_capture_batch.py.
6. Add sample manifest under:
   sample_data/lab_captures/lab_lv_monogram_batch_001/manifest.yaml
7. Validation should check:
   - manifest parses
   - protocol exists
   - files exist
   - files decode as images
   - SHA-256 checksums
   - duplicate SHA-256 detection
   - invalid region code rejection
   - required-region completeness
   - label validity
   - image quality metrics
8. Store validation results in capture_batch_validation_reports.
9. Add Makefile command:
   make validate-capture-batch BATCH=lab_lv_monogram_batch_001
10. Add documentation:
   docs/architecture/phase-8-real-capture-protocol-lab-ingestion.md
   docs/operations/capture-batch-manifest.md
   docs/operations/microscope-acceptance-test.md

Acceptance criteria:
1. docker compose up --build starts all services.
2. make health passes.
3. Existing smoke tests pass.
4. make validate-capture-batch BATCH=lab_lv_monogram_batch_001 works.
5. Validation report is persisted.
6. No production authentication claims are added.
```

---

## 21. Bottom Line

The platform is ready for the next logical step: **real capture readiness**.

The microscope does not need to exist yet for us to prepare the system. We can build the manifest format, capture protocol, validation gates, ingestion workflow, and dataset-promotion controls now.

When the microscope arrives, the first images should not be treated as random uploads. They should enter as a controlled capture batch with a manifest, validation report, calibration metadata, and dataset-governance path.
