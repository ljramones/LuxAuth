#!/usr/bin/env python3
"""Generate a sample lab capture batch with manifest for local testing.

Creates sample_data/lab_captures/smoke_lab_lv_monogram_batch_001/ with:
- manifest.yaml
- Synthetic images for 2 authentic + 2 counterfeit items
- 1 intentionally incomplete item (missing regions) for validation testing
"""

from pathlib import Path

import numpy as np
from PIL import Image

OUTPUT_DIR = Path("sample_data/lab_captures/smoke_lab_lv_monogram_batch_001")
REGIONS = ["EXTERIOR_CANVAS", "FRONT_LOGO_PRINT", "INTERIOR_HEAT_STAMP", "HARDWARE_ENGRAVING", "STITCHING_DETAIL"]
IMG_SIZE = 512


def make_texture(seed: int, roughness: float = 0.3) -> np.ndarray:
    rng = np.random.RandomState(seed)
    x = np.linspace(0, 4 * np.pi, IMG_SIZE)
    y = np.linspace(0, 4 * np.pi, IMG_SIZE)
    xx, yy = np.meshgrid(x, y)
    pattern = np.sin(xx * (2 + seed % 3)) * np.cos(yy * (2 + seed % 4))
    pattern = (pattern + 1) / 2
    noise = rng.normal(0, roughness, (IMG_SIZE, IMG_SIZE))
    r = np.clip((pattern + noise) * 180 + 40, 0, 255)
    g = np.clip((pattern + noise * 0.8) * 160 + 50, 0, 255)
    b = np.clip((pattern + noise * 0.6) * 140 + 60, 0, 255)
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def save_img(arr: np.ndarray, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(str(path), format="PNG")


def main():
    print("Generating lab capture batch: smoke_lab_lv_monogram_batch_001")

    items = [
        {"id": "lv_auth_001", "status": "CONFIRMED_AUTHENTIC", "roughness": 0.15, "seed_base": 1000},
        {"id": "lv_auth_002", "status": "CONFIRMED_AUTHENTIC", "roughness": 0.18, "seed_base": 1100},
        {"id": "lv_fake_001", "status": "CONFIRMED_COUNTERFEIT", "roughness": 0.55, "seed_base": 2000},
        {"id": "lv_fake_002", "status": "CONFIRMED_COUNTERFEIT", "roughness": 0.50, "seed_base": 2100},
        {"id": "lv_incomplete_001", "status": "CONFIRMED_AUTHENTIC", "roughness": 0.16, "seed_base": 3000, "incomplete": True},
    ]

    manifest_items = []
    for item in items:
        item_images = []
        regions_to_use = REGIONS[:2] if item.get("incomplete") else REGIONS  # incomplete: only 2 of 5

        for i, region in enumerate(regions_to_use):
            fname = f"{region.lower()}_01.png"
            rel_path = f"{item['id']}/{fname}"
            arr = make_texture(item["seed_base"] + i, item["roughness"])
            save_img(arr, OUTPUT_DIR / item["id"] / fname)
            item_images.append({"region_code": region, "file": rel_path})

        item_dict = {
            "external_item_id": item["id"],
            "brand": "Louis Vuitton",
            "category": "handbag",
            "material": "monogram_canvas",
            "model": None,
            "production_year": None,
            "authenticity_status": item["status"],
            "label_confidence": "high",
            "provenance_type": "synthetic",
            "notes": "Synthetic local-dev sample, not real product data.",
            "images": item_images,
        }

        # Add condition metadata to lv_auth_002 as a test case
        if item["id"] == "lv_auth_002":
            item_dict["condition"] = {
                "condition_grade": "used_good",
                "known_authenticity_basis": "expert_opinion",
                "known_repairs": True,
                "third_party_repair": True,
                "restoration_notes": "Restitched side seam with non-OEM thread",
                "provenance_notes": "Synthetic test item",
                "condition_notes": "Moderate wear, good overall condition",
            }
            item_dict["component_conditions"] = [
                {
                    "region_code": "STITCHING_DETAIL",
                    "component_type": "thread",
                    "component_status": "REPLACED_THIRD_PARTY",
                    "source": "owner_disclosed",
                    "confidence": "medium",
                    "exclude_from_auth_decision": False,
                    "expected_to_mismatch": True,
                    "notes": "Known non-OEM thread repair for testing",
                },
            ]

        manifest_items.append(item_dict)

    # Write manifest
    import yaml
    manifest = {
        "batch_code": "smoke_lab_lv_monogram_batch_001",
        "source_type": "lab_capture",
        "capture_protocol_code": "lv_monogram_canvas_handbag_capture",
        "capture_protocol_version": "v0.1.0",
        "device_code": "local_dev_microscope_001",
        "calibration_profile": "local_dev_calibration_v0.1.0",
        "operator": "local_dev",
        "notes": "Synthetic lab capture batch for workflow validation. NOT real product data.",
        "items": manifest_items,
    }

    manifest_path = OUTPUT_DIR / "manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    total_images = sum(len(item["images"]) for item in manifest_items)
    print(f"  Items: {len(manifest_items)}")
    print(f"  Images: {total_images}")
    print(f"  Incomplete items: {sum(1 for i in items if i.get('incomplete'))}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Manifest: {manifest_path}")
    print("NOTE: These are synthetic images for workflow testing only.")


if __name__ == "__main__":
    main()
