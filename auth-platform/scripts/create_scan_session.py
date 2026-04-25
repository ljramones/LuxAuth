#!/usr/bin/env python3
"""Create a scan session against the local scan-session-service."""

import json
import sys

import httpx

SCAN_SESSION_URL = "http://localhost:8101/scan-sessions"
ORGANIZATION_ID = "a0000000-0000-0000-0000-000000000001"
DEVICE_ID = "c0000000-0000-0000-0000-000000000001"


def create_scan_session() -> str:
    payload = {
        "claimed_brand": "Louis Vuitton",
        "claimed_category": "handbag",
        "claimed_material": "monogram_canvas",
        "device_id": DEVICE_ID,
        "organization_id": ORGANIZATION_ID,
    }

    response = httpx.post(SCAN_SESSION_URL, json=payload, timeout=10.0)
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, indent=2))

    scan_session_id = data.get("id") or data.get("scan_session_id")
    print(f"\nscan_session_id: {scan_session_id}")
    return scan_session_id


if __name__ == "__main__":
    try:
        session_id = create_scan_session()
    except httpx.ConnectError:
        print("ERROR: Could not connect to scan-session-service at localhost:8101.", file=sys.stderr)
        print("Make sure the stack is running: make up", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"ERROR: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)
