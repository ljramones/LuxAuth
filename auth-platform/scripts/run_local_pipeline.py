#!/usr/bin/env python3
"""
Run the full authentication pipeline locally.

Walks a fake image through every stage: session creation, upload,
quality check, normalization, embedding, vector search, region scoring,
and final decision.
"""

import httpx
import json
import sys
import os

# ── Seeded UUIDs (must match infra/postgres/init seed data) ──────────
ORGANIZATION_ID = "a0000000-0000-0000-0000-000000000001"
DEVICE_ID = "c0000000-0000-0000-0000-000000000001"

# ── Service URLs ─────────────────────────────────────────────────────
SCAN_SESSION_URL = "http://localhost:8101"
EVIDENCE_ASSET_URL = "http://localhost:8104"
IMAGE_QUALITY_URL = "http://localhost:8201"
NORMALIZATION_URL = "http://localhost:8202"
EMBEDDING_URL = "http://localhost:8203"
VECTOR_SEARCH_URL = "http://localhost:8204"
REGION_SCORING_URL = "http://localhost:8205"
DECISION_URL = "http://localhost:8301"

TIMEOUT = 15.0


def step(emoji: str, label: str):
    print(f"\n{emoji}  {label}")
    print("─" * 50)


def post(url: str, **kwargs) -> dict:
    response = httpx.post(url, timeout=TIMEOUT, **kwargs)
    response.raise_for_status()
    data = response.json()
    print(json.dumps(data, indent=2))
    return data


def main():
    print("=" * 60)
    print("  Auth Platform — Local Pipeline Smoke Test")
    print("=" * 60)

    # 1. Create scan session
    step("\u2705", "Step 1: Create scan session")
    session = post(
        f"{SCAN_SESSION_URL}/scan-sessions",
        json={
            "claimed_brand": "Louis Vuitton",
            "claimed_category": "handbag",
            "claimed_material": "monogram_canvas",
            "device_id": DEVICE_ID,
            "organization_id": ORGANIZATION_ID,
        },
    )
    scan_session_id = session.get("id") or session.get("scan_session_id")
    print(f"\n  scan_session_id = {scan_session_id}")

    # 2. Upload a fake image
    step("\U0001f4f7", "Step 2: Upload sample image")
    fake_image = os.urandom(100)
    upload_resp = httpx.post(
        f"{EVIDENCE_ASSET_URL}/scan-sessions/{scan_session_id}/images",
        files={"file": ("sample.jpg", fake_image, "image/jpeg")},
        data={"region_code": "EXTERIOR_CANVAS", "device_id": DEVICE_ID},
        timeout=TIMEOUT,
    )
    upload_resp.raise_for_status()
    upload_data = upload_resp.json()
    print(json.dumps(upload_data, indent=2))
    image_id = upload_data.get("id") or upload_data.get("image_asset_id")
    print(f"\n  image_id = {image_id}")

    # 3. Image quality assessment
    step("\U0001f50d", "Step 3: Image quality assessment")
    quality = post(f"{IMAGE_QUALITY_URL}/process/{image_id}")

    # 4. Normalization
    step("\U0001f4d0", "Step 4: Normalization")
    normalized = post(f"{NORMALIZATION_URL}/process/{image_id}")

    # 5. Embedding generation
    step("\U0001f9e0", "Step 5: Embedding generation")
    embedding = post(f"{EMBEDDING_URL}/process/{image_id}")

    # 6. Vector search
    step("\U0001f50e", "Step 6: Vector search")
    search_results = post(f"{VECTOR_SEARCH_URL}/search/{image_id}")

    # 7. Region scoring
    step("\U0001f4ca", "Step 7: Region scoring")
    score_payload = {
        "image_asset_id": image_id,
        "scan_session_id": scan_session_id,
        "region_code": "EXTERIOR_CANVAS",
        "authentic_similarity": search_results.get("authentic_cluster_score", 0.85),
        "counterfeit_similarity": search_results.get("counterfeit_cluster_score", 0.35),
        "ood_score": search_results.get("ood_score", 0.15),
    }
    region_score = post(f"{REGION_SCORING_URL}/score", json=score_payload)

    # 8. Final decision
    step("\u2696\ufe0f", "Step 8: Authentication decision")
    decision = post(f"{DECISION_URL}/decide/{scan_session_id}")

    # Summary
    print("\n" + "=" * 60)
    result = decision.get("result", decision.get("verdict", "UNKNOWN"))
    print(f"  \u2705  RESULT: {result}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError as e:
        print(f"\n\u274c  Connection error: {e}", file=sys.stderr)
        print("    Make sure the stack is running: make up", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"\n\u274c  HTTP error: {e.response.status_code} — {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n\u274c  Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
