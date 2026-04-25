# Capture Batch Manifest Format

## Structure

```yaml
batch_code: unique_batch_identifier
source_type: lab_capture | field_capture | partner_supplied
capture_protocol_code: lv_monogram_canvas_handbag_capture
device_code: device_serial_number
operator: operator_name
notes: Free-text notes about this batch.

items:
  - external_item_id: unique_item_identifier
    brand: Louis Vuitton
    category: handbag
    material: monogram_canvas
    authenticity_status: CONFIRMED_AUTHENTIC | CONFIRMED_COUNTERFEIT
    label_confidence: high | medium | low
    provenance_type: synthetic | expert_review | receipt_verified | partner_supplied
    images:
      - region_code: EXTERIOR_CANVAS
        file: relative/path/to/image.png
```

## Required Fields

- `batch_code`: unique identifier for the batch
- `capture_protocol_code`: must match an active protocol
- Items must have `external_item_id` and `authenticity_status`
- Images must have `region_code` and `file` (relative to batch directory)

## File Organization

```text
sample_data/lab_captures/{batch_code}/
  manifest.yaml
  {item_id}/
    exterior_canvas_01.png
    front_logo_01.png
    ...
```
