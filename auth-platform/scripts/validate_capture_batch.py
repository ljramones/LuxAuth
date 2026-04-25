#!/usr/bin/env python3
"""Validate a capture batch manifest and images.

Usage: python scripts/validate_capture_batch.py --batch lab_lv_monogram_batch_001 [--auto-create-device]
"""

import argparse
import importlib.util
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import yaml

# Import imaging
_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)
validate_image = _imaging.validate_image
compute_quality_metrics = _imaging.compute_quality_metrics

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
BASE_DIR = Path("sample_data/lab_captures")
ORG_ID = "a0000000-0000-0000-0000-000000000001"
VALID_STATUSES = {"CONFIRMED_AUTHENTIC", "CONFIRMED_COUNTERFEIT"}
VALID_CONFIDENCES = {"high", "medium", "low"}


SAFE_PREFIXES = ("smoke_", "synthetic_")


def _is_safe_to_cleanup(batch_code: str, force: bool) -> bool:
    """Only allow destructive cleanup for smoke/synthetic batches unless --force."""
    if any(batch_code.startswith(p) for p in SAFE_PREFIXES):
        return True
    return bool(force)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True)
    parser.add_argument("--auto-create-device", action="store_true")
    parser.add_argument("--force", action="store_true", help="Allow cleanup of non-smoke batches")
    args = parser.parse_args()

    batch_dir = BASE_DIR / args.batch
    manifest_path = batch_dir / "manifest.yaml"

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    errors = []
    warnings = []
    now = datetime.now(UTC)

    batch_code = manifest.get("batch_code")
    if not batch_code:
        errors.append("Missing batch_code in manifest")

    # Check protocol
    protocol_code = manifest.get("capture_protocol_code")
    cur.execute("SELECT id FROM capture_protocols WHERE protocol_code = %s AND status = 'active'", (protocol_code,))
    proto_row = cur.fetchone()
    protocol_id = proto_row[0] if proto_row else None
    if not protocol_id:
        errors.append(f"Protocol not found or inactive: {protocol_code}")

    # Get valid region codes from protocol
    valid_regions = set()
    region_min_images = {}
    if protocol_id:
        cur.execute("SELECT region_code, min_images FROM capture_protocol_regions WHERE capture_protocol_id = %s", (str(protocol_id),))
        for rc, mi in cur.fetchall():
            valid_regions.add(rc)
            region_min_images[rc] = mi

    # Check/create device
    device_code = manifest.get("device_code", "")
    cur.execute("SELECT id FROM devices WHERE device_serial = %s", (device_code,))
    dev_row = cur.fetchone()
    device_id = dev_row[0] if dev_row else None
    if not device_id and args.auto_create_device:
        device_id = str(uuid.uuid4())
        cur.execute("INSERT INTO devices (id, organization_id, device_serial, device_type, status) VALUES (%s, %s, %s, %s, 'ACTIVE')",
                    (device_id, ORG_ID, device_code, "LAB_MICROSCOPE"))
        warnings.append(f"Auto-created device: {device_code}")
    elif not device_id:
        errors.append(f"Device not found: {device_code}. Use --auto-create-device")

    # Clean previous batch data (with safety guard)
    cur.execute("SELECT id FROM capture_batches WHERE batch_code = %s", (batch_code,))
    old = cur.fetchone()
    if old:
        if not _is_safe_to_cleanup(batch_code, args.force):
            print(f"ERROR: Refusing to delete existing batch '{batch_code}'. Use --force for non-smoke batches.")
            sys.exit(1)
        old_id = old[0]
        cur.execute("DELETE FROM capture_batch_validation_reports WHERE capture_batch_id = %s", (str(old_id),))
        cur.execute("DELETE FROM capture_batch_images WHERE capture_batch_id = %s", (str(old_id),))
        cur.execute("DELETE FROM capture_batch_items WHERE capture_batch_id = %s", (str(old_id),))
        cur.execute("DELETE FROM capture_batches WHERE id = %s", (str(old_id),))

    # Create batch record
    batch_id = str(uuid.uuid4())
    cur.execute("""INSERT INTO capture_batches (id, batch_code, capture_protocol_id, device_id, source_type, status, created_by, notes, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, 'VALIDATING', %s, %s, %s, %s)""",
                (batch_id, batch_code, str(protocol_id) if protocol_id else None,
                 str(device_id) if device_id else None, manifest.get("source_type", "lab_capture"),
                 manifest.get("operator"), manifest.get("notes"), now, now))

    # Validate items and images
    items = manifest.get("items", [])
    total_images = 0
    quality_fails = 0
    sha256_set = set()
    duplicates = 0

    for item_data in items:
        ext_id = item_data.get("external_item_id", "UNKNOWN")
        auth_status = item_data.get("authenticity_status", "")
        if auth_status not in VALID_STATUSES:
            errors.append(f"Item {ext_id}: invalid authenticity_status '{auth_status}'")

        label_conf = item_data.get("label_confidence", "high")
        if label_conf not in VALID_CONFIDENCES:
            warnings.append(f"Item {ext_id}: unusual label_confidence '{label_conf}'")

        item_id = str(uuid.uuid4())
        cur.execute("""INSERT INTO capture_batch_items (id, capture_batch_id, external_item_id, brand, category, material, model, production_year, authenticity_status, label_confidence, provenance_type, status, notes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CREATED', %s)""",
                    (item_id, batch_id, ext_id, item_data.get("brand"), item_data.get("category"),
                     item_data.get("material"), item_data.get("model"), item_data.get("production_year"),
                     auth_status, label_conf, item_data.get("provenance_type", "synthetic"),
                     item_data.get("notes")))

        # Validate optional condition metadata
        condition = item_data.get("condition")
        if condition:
            valid_grades = {"pristine", "used_good", "used_fair", "heavily_worn"}
            grade = condition.get("condition_grade")
            if grade and grade not in valid_grades:
                warnings.append(f"Item {ext_id}: unusual condition_grade '{grade}'")

        # Validate optional component conditions
        components = item_data.get("component_conditions", [])
        for comp in components:
            comp_region = comp.get("region_code", "")
            if comp_region and comp_region not in valid_regions and valid_regions:
                errors.append(f"Item {ext_id}: invalid component region '{comp_region}'. Valid: {sorted(valid_regions)}")

        # Persist condition metadata if present
        if condition:
            cond_id = str(uuid.uuid4())
            cur.execute("""INSERT INTO item_condition_metadata
                           (id, capture_batch_item_id, condition_grade, known_authenticity_basis,
                            known_repairs, third_party_repair, restoration_notes, provenance_notes, condition_notes)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (cond_id, item_id,
                         condition.get("condition_grade"),
                         condition.get("known_authenticity_basis"),
                         condition.get("known_repairs", False),
                         condition.get("third_party_repair", False),
                         condition.get("restoration_notes"),
                         condition.get("provenance_notes"),
                         condition.get("condition_notes")))

            # Persist component conditions
            for comp in components:
                cur.execute("""INSERT INTO item_component_conditions
                               (id, item_condition_metadata_id, region_code, component_type,
                                component_status, source, confidence, exclude_from_auth_decision,
                                expected_to_mismatch, notes)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (str(uuid.uuid4()), cond_id,
                             comp.get("region_code"), comp.get("component_type"),
                             comp.get("component_status"), comp.get("source"),
                             comp.get("confidence"), comp.get("exclude_from_auth_decision", False),
                             comp.get("expected_to_mismatch", False), comp.get("notes")))

        # Check region completeness for this item
        item_region_counts = {}
        for img_data in item_data.get("images", []):
            region = img_data.get("region_code", "")
            file_rel = img_data.get("file", "")
            file_path = batch_dir / file_rel

            if region not in valid_regions and valid_regions:
                errors.append(f"Item {ext_id}: invalid region '{region}'. Valid: {sorted(valid_regions)}")
                continue

            img_id = str(uuid.uuid4())
            img_status = "CREATED"
            img_issues = []
            img_meta = {}

            if not file_path.exists():
                errors.append(f"Item {ext_id}: file not found: {file_rel}")
                img_status = "FILE_MISSING"
            else:
                raw_bytes = file_path.read_bytes()
                validation = validate_image(raw_bytes)
                sha256 = validation.get("sha256_checksum", "")

                if sha256 in sha256_set:
                    duplicates += 1
                    warnings.append(f"Item {ext_id}: duplicate SHA-256 for {file_rel}")
                sha256_set.add(sha256)

                if not validation.get("valid", False):
                    errors.append(f"Item {ext_id}: invalid image {file_rel}: {validation.get('issues')}")
                    img_status = "INVALID"
                    img_issues = validation.get("issues", [])
                else:
                    quality = compute_quality_metrics(raw_bytes)
                    if quality["quality_status"] == "FAIL":
                        quality_fails += 1
                        warnings.append(f"Item {ext_id}: quality FAIL for {file_rel}: {quality['issues']}")
                    img_meta = {
                        "width": validation.get("width"),
                        "height": validation.get("height"),
                        "image_format": validation.get("image_format"),
                        "color_mode": validation.get("color_mode"),
                        "sha256_checksum": sha256,
                        "quality_status": quality["quality_status"],
                        "issues": quality.get("issues", []),
                    }
                    img_status = "VALIDATED"

            cur.execute("""INSERT INTO capture_batch_images (id, capture_batch_id, capture_batch_item_id, region_code, source_file_path, sha256_checksum, width, height, image_format, color_mode, quality_status, issues, status)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (img_id, batch_id, item_id, region, str(file_path),
                         img_meta.get("sha256_checksum"), img_meta.get("width"), img_meta.get("height"),
                         img_meta.get("image_format"), img_meta.get("color_mode"),
                         img_meta.get("quality_status"), json.dumps(img_meta.get("issues", img_issues)),
                         img_status))

            item_region_counts[region] = item_region_counts.get(region, 0) + 1
            total_images += 1

        # Check region completeness
        for rc, min_img in region_min_images.items():
            count = item_region_counts.get(rc, 0)
            if count < min_img:
                warnings.append(f"Item {ext_id}: {rc} has {count}/{min_img} images (below minimum)")

    # Determine batch status
    fatal = len(errors) > 0
    batch_status = "FAILED" if fatal else ("VALIDATED_WITH_WARNINGS" if warnings else "VALIDATED")
    cur.execute("UPDATE capture_batches SET status = %s, updated_at = %s WHERE id = %s",
                (batch_status, now, batch_id))

    summary = {
        "item_count": len(items),
        "image_count": total_images,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "duplicate_count": duplicates,
        "quality_fail_count": quality_fails,
        "status": batch_status,
    }

    cur.execute("INSERT INTO capture_batch_validation_reports (id, capture_batch_id, status, summary_json) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), batch_id, batch_status, json.dumps(summary)))

    # Audit
    cur.execute("INSERT INTO audit_events (id, event_type, payload, created_at) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()),
                 "CAPTURE_BATCH_VALIDATED" if not fatal else "CAPTURE_BATCH_VALIDATION_FAILED",
                 json.dumps({"batch_code": batch_code, "status": batch_status}), now))

    # Print report
    print("=" * 60)
    print("  CAPTURE BATCH VALIDATION REPORT")
    print("=" * 60)
    print(f"\n  Batch:      {batch_code}")
    print(f"  Status:     {batch_status}")
    print(f"  Items:      {len(items)}")
    print(f"  Images:     {total_images}")
    print(f"  Errors:     {len(errors)}")
    print(f"  Warnings:   {len(warnings)}")
    print(f"  Duplicates: {duplicates}")
    print(f"  Quality fails: {quality_fails}")

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"    - {e}")
    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    - {w}")

    print(f"\n{'=' * 60}")
    cur.close()
    conn.close()

    sys.exit(1 if fatal else 0)


if __name__ == "__main__":
    main()
