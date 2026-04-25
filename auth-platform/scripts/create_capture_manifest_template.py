#!/usr/bin/env python3
"""Create a starter capture manifest from the default protocol.

Usage:
  python3 scripts/create_capture_manifest_template.py \
    --batch-code lab_first_real_batch_001 \
    --device-code DINO-LITE-001 \
    --output sample_data/lab_captures/lab_first_real_batch_001/manifest.yaml
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
import yaml

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def main():
    parser = argparse.ArgumentParser(description="Create a starter capture manifest")
    parser.add_argument("--batch-code", required=True, help="Unique batch code")
    parser.add_argument("--device-code", default="REPLACE_WITH_DEVICE_SERIAL")
    parser.add_argument("--calibration-profile", default="REPLACE_WITH_CALIBRATION_NAME")
    parser.add_argument("--protocol", default="lv_monogram_canvas_handbag_capture")
    parser.add_argument("--operator", default="REPLACE_WITH_OPERATOR")
    parser.add_argument("--items", type=int, default=2, help="Number of item stubs to generate")
    parser.add_argument("--output", required=True, help="Output manifest path")
    args = parser.parse_args()

    # Look up protocol regions from DB
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT cpr.region_code, cpr.min_images
        FROM capture_protocol_regions cpr
        JOIN capture_protocols cp ON cp.id = cpr.capture_protocol_id
        WHERE cp.protocol_code = %s AND cp.status = 'active'
        ORDER BY cpr.sort_order
    """, (args.protocol,))
    regions = cur.fetchall()
    cur.close()
    conn.close()

    if not regions:
        print(f"Protocol not found or has no regions: {args.protocol}")
        print("Make sure the stack is running: make health")
        sys.exit(1)

    # Build item stubs
    items = []
    for i in range(1, args.items + 1):
        item_id = f"item_{i:03d}"
        images = []
        for region_code, min_images in regions:
            for j in range(1, min_images + 1):
                fname = f"{region_code.lower()}_{j:02d}.png"
                images.append({
                    "region_code": region_code,
                    "file": f"{item_id}/{fname}",
                })
        items.append({
            "external_item_id": item_id,
            "brand": "Louis Vuitton",
            "category": "handbag",
            "material": "monogram_canvas",
            "model": None,
            "production_year": None,
            "authenticity_status": "CONFIRMED_AUTHENTIC",
            "label_confidence": "high",
            "provenance_type": "REPLACE_WITH_PROVENANCE",
            "notes": "REPLACE: How was this item authenticated?",
            "images": images,
        })

    manifest = {
        "batch_code": args.batch_code,
        "source_type": "lab_capture",
        "capture_protocol_code": args.protocol,
        "capture_protocol_version": "v0.1.0",
        "device_code": args.device_code,
        "calibration_profile": args.calibration_profile,
        "operator": args.operator,
        "notes": "REPLACE: Describe this capture session.",
        "items": items,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Manifest created: {out_path}")
    print(f"  Protocol: {args.protocol}")
    print(f"  Regions: {len(regions)}")
    print(f"  Items: {args.items}")
    total = sum(min_img for _, min_img in regions) * args.items
    print(f"  Image placeholders: {total}")
    print(f"\nNext: place images in {out_path.parent}/ and edit the manifest.")
    print("See: docs/operations/microscope-acceptance-runbook.md")


if __name__ == "__main__":
    main()
