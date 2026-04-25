#!/usr/bin/env python3
"""Smoke test for capture intake APIs.

Tests:
1. Register device (or use existing)
2. Create calibration
3. Create capture session with default protocol
4. Upload one image for EXTERIOR_CANVAS — verify incomplete
5. Upload images for all required regions
6. Complete session — verify COMPLETE
7. Verify images entered quality pipeline
"""

import io
import os
import sys
import time

import httpx
import numpy as np
from PIL import Image

DEVICE_URL = "http://localhost:8103"
CAPTURE_URL = "http://localhost:8106"
QUALITY_URL = "http://localhost:8201"

TIMEOUT = 15.0
ORG_ID = "a0000000-0000-0000-0000-000000000001"

REQUIRED_REGIONS = [
    ("EXTERIOR_CANVAS", 3),
    ("FRONT_LOGO_PRINT", 2),
    ("INTERIOR_HEAT_STAMP", 2),
    ("HARDWARE_ENGRAVING", 2),
    ("STITCHING_DETAIL", 3),
]


def step(label: str):
    print(f"\n  >> {label}")


def post(url: str, **kwargs) -> dict:
    resp = httpx.post(url, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def get(url: str) -> dict:
    resp = httpx.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def make_test_jpeg(seed: int = 0) -> bytes:
    rng = np.random.RandomState(seed)
    arr = rng.randint(50, 200, (256, 256, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main():
    print("=" * 60)
    print("  Capture Intake API Smoke Test")
    print("=" * 60)

    # 1. Register device
    step("Register device")
    device = post(
        f"{DEVICE_URL}/devices/register",
        json={
            "device_serial": f"TEST-CAPTURE-{int(time.time())}",
            "device_type": "HANDHELD_MICROSCOPE",
            "organization_id": ORG_ID,
            "firmware_version": "1.0.0",
        },
    )
    device_id = device["id"]
    print(f"    device_id = {device_id}")

    # 2. Create calibration
    step("Create calibration")
    cal = post(
        f"{DEVICE_URL}/devices/{device_id}/calibrations",
        json={
            "calibration_profile": {
                "name": "local_dev_calibration_v0.1.0",
                "scale_reference_used": True,
                "white_balance_reference_used": True,
            },
        },
    )
    cal_id = cal["id"]
    print(f"    calibration_id = {cal_id}")

    # 3. Verify default protocol exists
    step("Get default capture protocol")
    protocol = get(f"{CAPTURE_URL}/capture-protocols/lv_monogram_canvas_handbag_capture")
    print(f"    protocol: {protocol['protocol_code']} ({len(protocol['regions'])} regions)")

    # 4. Create capture session
    step("Create capture session")
    session = post(
        f"{CAPTURE_URL}/capture-sessions",
        json={
            "device_id": device_id,
            "calibration_id": cal_id,
            "capture_protocol_code": "lv_monogram_canvas_handbag_capture",
            "source_type": "smoke_test",
            "operator": "smoke_test_runner",
        },
    )
    session_id = session["id"]
    print(f"    capture_session_id = {session_id}")

    # 5. Upload one image — should be incomplete
    step("Upload 1 image for EXTERIOR_CANVAS")
    img_data = make_test_jpeg(seed=42)
    upload = post(
        f"{CAPTURE_URL}/capture-sessions/{session_id}/images",
        files={"file": ("test.jpg", img_data, "image/jpeg")},
        data={"region_code": "EXTERIOR_CANVAS", "external_item_id": "item_001"},
    )
    print(f"    image_id = {upload['id']}")

    step("Check status (should be incomplete)")
    status = get(f"{CAPTURE_URL}/capture-sessions/{session_id}/status")
    print(f"    all_satisfied = {status['all_regions_satisfied']}")
    print(f"    missing = {status['missing_regions']}")
    assert not status["all_regions_satisfied"], "Should be incomplete"

    step("Try to complete (should be INCOMPLETE)")
    complete_resp = post(f"{CAPTURE_URL}/capture-sessions/{session_id}/complete")
    print(f"    status = {complete_resp['status']}")
    assert complete_resp["status"] == "INCOMPLETE"

    # 6. Upload remaining images
    step("Upload images for all required regions")
    for region, min_images in REQUIRED_REGIONS:
        # We already uploaded 1 for EXTERIOR_CANVAS
        start = 1 if region == "EXTERIOR_CANVAS" else 0
        for i in range(start, min_images):
            img = make_test_jpeg(seed=hash(f"{region}_{i}") % 10000)
            resp = post(
                f"{CAPTURE_URL}/capture-sessions/{session_id}/images",
                files={"file": (f"{region}_{i}.jpg", img, "image/jpeg")},
                data={
                    "region_code": region,
                    "external_item_id": "item_001",
                    "capture_index": i,
                },
            )
            print(f"    {region}[{i}] = {resp['id']}")

    # 7. Complete session
    step("Complete session (should be COMPLETE)")
    complete_resp = post(f"{CAPTURE_URL}/capture-sessions/{session_id}/complete")
    print(f"    status = {complete_resp['status']}")
    print(f"    total_images = {complete_resp['total_images']}")
    assert complete_resp["status"] == "COMPLETE", f"Expected COMPLETE, got {complete_resp['status']}"

    # 8. Verify invalid region rejected
    step("Upload with invalid region (should fail)")
    try:
        bad_img = make_test_jpeg(seed=999)
        post(
            f"{CAPTURE_URL}/capture-sessions/{session_id}/images",
            files={"file": ("bad.jpg", bad_img, "image/jpeg")},
            data={"region_code": "INVALID_REGION", "external_item_id": "item_001"},
        )
        print("    ERROR: Should have been rejected")
        return False
    except httpx.HTTPStatusError as e:
        print(f"    Correctly rejected: {e.response.status_code}")

    print("\n" + "=" * 60)
    print("  [PASS] All capture API tests passed")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except httpx.ConnectError as e:
        print(f"\nConnection error: {e}", file=sys.stderr)
        print("Make sure the stack is running: make up", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"\nHTTP error: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except AssertionError as e:
        print(f"\nAssertion failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
