#!/usr/bin/env python3
"""Upload a sample (fake) image to the evidence-asset-service."""

import json
import os
import sys

import httpx

EVIDENCE_ASSET_URL = "http://localhost:8104/scan-sessions"
DEVICE_ID = "c0000000-0000-0000-0000-000000000001"


def upload_sample_image(scan_session_id: str) -> str:
    url = f"{EVIDENCE_ASSET_URL}/{scan_session_id}/images"

    # Create a small fake image (100 bytes of random data)
    fake_image = os.urandom(100)

    files = {
        "file": ("sample_image.jpg", fake_image, "image/jpeg"),
    }
    data = {
        "region_code": "EXTERIOR_CANVAS",
        "device_id": DEVICE_ID,
    }

    response = httpx.post(url, files=files, data=data, timeout=10.0)
    response.raise_for_status()

    result = response.json()
    print(json.dumps(result, indent=2))

    image_asset_id = result.get("id") or result.get("image_asset_id")
    print(f"\nimage_asset_id: {image_asset_id}")
    return image_asset_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_sample_image.py <scan_session_id>", file=sys.stderr)
        print("       Or import and call upload_sample_image(scan_session_id)", file=sys.stderr)
        sys.exit(1)

    scan_session_id = sys.argv[1]

    try:
        image_id = upload_sample_image(scan_session_id)
    except httpx.ConnectError:
        print("ERROR: Could not connect to evidence-asset-service at localhost:8104.", file=sys.stderr)
        print("Make sure the stack is running: make up", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"ERROR: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)
