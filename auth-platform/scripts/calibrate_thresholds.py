#!/usr/bin/env python3
"""Sweep thresholds to find optimal scoring configuration.

Usage: python scripts/calibrate_thresholds.py --model texture_baseline_v0.1.0 [--write-profile]
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from itertools import product

import numpy as np
import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def parse_vec(v):
    if isinstance(v, (list, np.ndarray)):
        return np.array(v, dtype=float)
    return np.array([float(x) for x in str(v).strip("[]").split(",")], dtype=float)


def cosine_sim(a, b):
    d = np.dot(a, b)
    n = np.linalg.norm(a) * np.linalg.norm(b)
    return float(d / n) if n > 0 else 0.0


def evaluate_thresholds(test_items, search_items, strong_thresh, mismatch_thresh):
    """Evaluate a threshold pair and return metrics."""
    tp = tn = fp = fn = inc = er = 0
    for t in test_items:
        sims = []
        for s in search_items:
            if s["id"] == t["id"] or s["region"] != t["region"]:
                continue
            sim = cosine_sim(t["emb"], s["emb"])
            sims.append({"sim": sim, "label": s["label"]})

        auth_sims = [x["sim"] for x in sims if "AUTHENTIC" in x["label"]]
        counter_sims = [x["sim"] for x in sims if "COUNTERFEIT" in x["label"]]
        auth_score = np.mean(auth_sims) if auth_sims else 0.0
        counter_score = np.mean(counter_sims) if counter_sims else 0.0

        if auth_score >= strong_thresh and counter_score < mismatch_thresh:
            predicted = "VERIFIED"
        elif counter_score > auth_score:
            predicted = "UNVERIFIED"
        elif auth_score >= 0.60:
            predicted = "EXPERT_REVIEW"
        else:
            predicted = "INCONCLUSIVE"

        expected = "AUTHENTIC" if "AUTHENTIC" in t["label"] else "COUNTERFEIT"
        if expected == "AUTHENTIC" and predicted == "VERIFIED":
            tp += 1
        elif expected == "COUNTERFEIT" and predicted == "UNVERIFIED":
            tn += 1
        elif expected == "COUNTERFEIT" and predicted == "VERIFIED":
            fp += 1
        elif expected == "AUTHENTIC" and predicted == "UNVERIFIED":
            fn += 1
        elif predicted == "EXPERT_REVIEW":
            er += 1
        else:
            inc += 1

    total = tp + tn + fp + fn + inc + er
    auth_total = tp + fn + er // 2 + inc // 2  # approximate
    counter_total = tn + fp + er // 2 + inc // 2
    return {
        "strong": strong_thresh, "mismatch": mismatch_thresh,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn, "inc": inc, "er": er,
        "fpr": fp / max(counter_total, 1), "fnr": fn / max(auth_total, 1),
        "accuracy": (tp + tn) / max(total, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="synthetic_lv_monogram_v0.1.0")
    parser.add_argument("--write-profile", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cur = conn.cursor()

    # Load validation/test items
    cur.execute("""
        SELECT re.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = %s AND rdv.dataset_version = %s
          AND dm.include_in_evaluation = TRUE
    """, (args.model, args.dataset))
    test_items = [{"id": str(r[0]), "emb": parse_vec(r[1]), "region": r[2], "label": r[3]} for r in cur.fetchall()]

    cur.execute("""
        SELECT re.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = %s AND rdv.dataset_version = %s
          AND dm.include_in_search = TRUE
    """, (args.model, args.dataset))
    search_items = [{"id": str(r[0]), "emb": parse_vec(r[1]), "region": r[2], "label": r[3]} for r in cur.fetchall()]

    print("=" * 70)
    print("  THRESHOLD CALIBRATION")
    print("=" * 70)
    print(f"  Model: {args.model}")
    print(f"  Dataset: {args.dataset}")
    print(f"  Test items: {len(test_items)}")
    print(f"  Search items: {len(search_items)}")

    # Sweep
    strong_range = np.arange(0.65, 0.96, 0.05)
    mismatch_range = np.arange(0.35, 0.66, 0.05)

    results = []
    for st, mm in product(strong_range, mismatch_range):
        r = evaluate_thresholds(test_items, search_items, st, mm)
        results.append(r)

    # Find best by different criteria
    no_fp = [r for r in results if r["fp"] == 0]
    best_conservative = min(no_fp, key=lambda r: r["fn"] + r["inc"] + r["er"]) if no_fp else min(results, key=lambda r: r["fp"])
    best_balanced = max(results, key=lambda r: r["accuracy"])
    best_zero_fp = min(no_fp, key=lambda r: r["fnr"]) if no_fp else None

    print(f"\n  Sweep: {len(results)} threshold combinations tested\n")

    for name, best in [("Conservative (min FP)", best_conservative), ("Balanced accuracy", best_balanced), ("Zero FP, min FN", best_zero_fp)]:
        if not best:
            continue
        print(f"  {name}:")
        print(f"    strong_match={best['strong']:.2f}, mismatch={best['mismatch']:.2f}")
        print(f"    TP={best['tp']} TN={best['tn']} FP={best['fp']} FN={best['fn']} INC={best['inc']} ER={best['er']}")
        print(f"    FPR={best['fpr']:.2%} FNR={best['fnr']:.2%} Accuracy={best['accuracy']:.2%}")
        print()

    if args.write_profile and best_conservative:
        b = best_conservative
        profile_name = f"{args.model}_calibrated"
        cur.execute("""
            INSERT INTO threshold_profiles (id, profile_name, profile_version, embedding_model_version,
                reference_dataset_version, strong_match_threshold, mismatch_threshold,
                ood_threshold, counterfeit_similarity_threshold, min_required_regions,
                require_all_regions, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 5, TRUE, 'draft')
        """, (str(uuid.uuid4()), profile_name, "v0.1.0", args.model, args.dataset,
              b["strong"], b["mismatch"], 0.40, b["mismatch"]))
        print(f"  Written draft profile: {profile_name}")

    print(f"{'=' * 70}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
