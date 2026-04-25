#!/usr/bin/env python3
"""Run an evaluation of the embedding model against the test split of a dataset.

For each test-split reference image:
1. Look up its reference embedding
2. Run vector search against search-eligible reference embeddings (excluding self)
3. Compute region-level similarity scores
4. Determine predicted label based on threshold profile
5. Compare to expected label
6. Record results

Usage: python scripts/run_evaluation.py [--dataset synthetic_lv_monogram_v0.1.0] [--profile texture_baseline_default]
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import numpy as np

# Import imaging module directly
import importlib.util
_imaging_path = str(Path(__file__).parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py")
_spec = importlib.util.spec_from_file_location("imaging", _imaging_path)
_imaging = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_imaging)

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def parse_pgvector(vec_str):
    """Parse a pgvector string like '[0.1,0.2,...]' into a list of floats."""
    if isinstance(vec_str, (list, np.ndarray)):
        return list(vec_str)
    s = str(vec_str).strip("[]")
    return [float(x) for x in s.split(",")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="synthetic_lv_monogram_v0.1.0")
    parser.add_argument("--profile", default="texture_baseline_default")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    # Load dataset version
    cur.execute("SELECT id, dataset_version FROM reference_dataset_versions WHERE dataset_version = %s", (args.dataset,))
    ds_row = cur.fetchone()
    if not ds_row:
        print(f"Dataset version not found: {args.dataset}")
        sys.exit(1)
    ds_id = ds_row[0]
    print(f"Dataset: {args.dataset}")

    # Load threshold profile
    cur.execute("SELECT * FROM threshold_profiles WHERE profile_name = %s AND status = 'active'", (args.profile,))
    profile_cols = [desc[0] for desc in cur.description]
    profile_row = cur.fetchone()
    if not profile_row:
        print(f"Threshold profile not found: {args.profile}")
        sys.exit(1)
    profile = dict(zip(profile_cols, profile_row))
    print(f"Profile: {profile['profile_name']}:{profile['profile_version']}")
    print(f"Thresholds: strong={profile['strong_match_threshold']}, mismatch={profile['mismatch_threshold']}")

    # Get test-split images with their embeddings
    cur.execute("""
        SELECT dm.reference_image_id, re.embedding, ri.region_code,
               rit.authenticity_status, dm.split
        FROM reference_dataset_members dm
        JOIN reference_embeddings re ON re.reference_image_id = dm.reference_image_id
        JOIN reference_images ri ON ri.id = dm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE dm.dataset_version_id = %s AND dm.include_in_evaluation = TRUE
        ORDER BY ri.region_code, rit.authenticity_status
    """, (str(ds_id),))
    test_cols = [desc[0] for desc in cur.description]
    test_rows = [dict(zip(test_cols, r)) for r in cur.fetchall()]
    print(f"Test items: {len(test_rows)}")

    if not test_rows:
        print("No test items found. Run: make ingest-reference-data")
        sys.exit(1)

    # Get search-eligible reference embeddings
    cur.execute("""
        SELECT dm.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_dataset_members dm
        JOIN reference_embeddings re ON re.reference_image_id = dm.reference_image_id
        JOIN reference_images ri ON ri.id = dm.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE dm.dataset_version_id = %s AND dm.include_in_search = TRUE
        ORDER BY ri.region_code
    """, (str(ds_id),))
    search_cols = [desc[0] for desc in cur.description]
    search_rows = [dict(zip(search_cols, r)) for r in cur.fetchall()]
    print(f"Search references: {len(search_rows)}")

    # Create evaluation run
    eval_id = str(uuid.uuid4())
    eval_name = f"eval_{args.dataset}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    now = datetime.now(timezone.utc)

    cur.execute("""
        INSERT INTO evaluation_runs (id, evaluation_name, reference_dataset_version,
            embedding_model_version, preprocessing_version, threshold_profile,
            started_at, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'RUNNING')
    """, (eval_id, eval_name, args.dataset, profile["embedding_model_version"],
          "normalize_image_v0.1.0", f"{profile['profile_name']}:{profile['profile_version']}", now))

    # Evaluate each test item
    results = []
    strong_thresh = profile["strong_match_threshold"]
    mismatch_thresh = profile["mismatch_threshold"]

    for test_item in test_rows:
        test_emb = parse_pgvector(test_item["embedding"])
        test_region = test_item["region_code"]
        test_ref_id = test_item["reference_image_id"]
        expected = test_item["authenticity_status"]  # CONFIRMED_AUTHENTIC or CONFIRMED_COUNTERFEIT

        # Find nearest references in same region, excluding self
        similarities = []
        for ref in search_rows:
            if str(ref["reference_image_id"]) == str(test_ref_id):
                continue  # exclude self
            if ref["region_code"] != test_region:
                continue  # same region only
            ref_emb = parse_pgvector(ref["embedding"])
            sim = cosine_similarity(test_emb, ref_emb)
            similarities.append({
                "similarity": sim,
                "authenticity_status": ref["authenticity_status"],
            })

        # Split into authentic/counterfeit
        auth_sims = [s["similarity"] for s in similarities if s["authenticity_status"] == "CONFIRMED_AUTHENTIC"]
        counter_sims = [s["similarity"] for s in similarities if s["authenticity_status"] == "CONFIRMED_COUNTERFEIT"]

        auth_score = sum(auth_sims) / len(auth_sims) if auth_sims else 0.0
        counter_score = sum(counter_sims) / len(counter_sims) if counter_sims else 0.0
        max_sim = max(auth_sims + counter_sims, default=0.0)
        ood = 1.0 - max_sim

        # Predict
        if auth_score >= strong_thresh and counter_score < mismatch_thresh:
            predicted = "VERIFIED"
        elif counter_score > auth_score:
            predicted = "UNVERIFIED"
        elif auth_score >= 0.60:
            predicted = "EXPERT_REVIEW_REQUIRED"
        else:
            predicted = "INCONCLUSIVE"

        # Map expected to simplified label
        expected_simple = "AUTHENTIC" if "AUTHENTIC" in expected else "COUNTERFEIT"

        # Determine correctness
        if expected_simple == "AUTHENTIC" and predicted == "VERIFIED":
            result = "TRUE_POSITIVE"
        elif expected_simple == "COUNTERFEIT" and predicted == "UNVERIFIED":
            result = "TRUE_NEGATIVE"
        elif expected_simple == "COUNTERFEIT" and predicted == "VERIFIED":
            result = "FALSE_POSITIVE"
        elif expected_simple == "AUTHENTIC" and predicted == "UNVERIFIED":
            result = "FALSE_NEGATIVE"
        elif predicted in ("INCONCLUSIVE", "EXPERT_REVIEW_REQUIRED"):
            result = predicted
        else:
            result = "OTHER"

        results.append({
            "reference_image_id": str(test_ref_id),
            "expected": expected_simple,
            "predicted": predicted,
            "result": result,
            "region_code": test_region,
            "auth_score": auth_score,
            "counter_score": counter_score,
            "ood": ood,
        })

        # Insert evaluation_item
        cur.execute("""
            INSERT INTO evaluation_items (id, evaluation_run_id, reference_image_id,
                expected_label, predicted_label, result, region_code,
                authentic_similarity, counterfeit_similarity, ood_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), eval_id, str(test_ref_id),
              expected_simple, predicted, result, test_region,
              round(auth_score, 4), round(counter_score, 4), round(ood, 4)))

    # Compute summary
    total = len(results)
    auth_items = sum(1 for r in results if r["expected"] == "AUTHENTIC")
    counter_items = sum(1 for r in results if r["expected"] == "COUNTERFEIT")
    tp = sum(1 for r in results if r["result"] == "TRUE_POSITIVE")
    tn = sum(1 for r in results if r["result"] == "TRUE_NEGATIVE")
    fp = sum(1 for r in results if r["result"] == "FALSE_POSITIVE")
    fn = sum(1 for r in results if r["result"] == "FALSE_NEGATIVE")
    inconclusive = sum(1 for r in results if r["result"] == "INCONCLUSIVE")
    expert_review = sum(1 for r in results if r["result"] == "EXPERT_REVIEW_REQUIRED")

    summary = {
        "total_items": total,
        "authentic_items": auth_items,
        "counterfeit_items": counter_items,
        "true_positive_count": tp,
        "true_negative_count": tn,
        "false_positive_count": fp,
        "false_negative_count": fn,
        "inconclusive_count": inconclusive,
        "expert_review_count": expert_review,
        "authentic_recall": round(tp / auth_items, 4) if auth_items else 0.0,
        "counterfeit_recall": round(tn / counter_items, 4) if counter_items else 0.0,
        "false_positive_rate": round(fp / counter_items, 4) if counter_items else 0.0,
        "false_negative_rate": round(fn / auth_items, 4) if auth_items else 0.0,
        "inconclusive_rate": round(inconclusive / total, 4) if total else 0.0,
        "expert_review_rate": round(expert_review / total, 4) if total else 0.0,
    }

    # Update evaluation run
    cur.execute("""
        UPDATE evaluation_runs SET status = 'COMPLETED', completed_at = %s, summary_json = %s
        WHERE id = %s
    """, (datetime.now(timezone.utc), json.dumps(summary), eval_id))

    # Record audit event
    cur.execute("""
        INSERT INTO audit_events (id, event_type, payload, created_at)
        VALUES (%s, 'EVALUATION_RUN_COMPLETED', %s, %s)
    """, (str(uuid.uuid4()), json.dumps({"evaluation_run_id": eval_id, "summary": summary}), now))

    print(f"\nEvaluation complete: {eval_name}")
    print(f"Run ID: {eval_id}")
    print(json.dumps(summary, indent=2))

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
