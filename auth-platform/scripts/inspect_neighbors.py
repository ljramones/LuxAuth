#!/usr/bin/env python3
"""Inspect nearest neighbors for test-split images.

Usage: python scripts/inspect_neighbors.py --model texture_baseline_v0.1.0 [--k 5] [--output reports/neighbors]
"""

import argparse
import json
import os
import sys
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="synthetic_lv_monogram_v0.1.0")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Load test items
    cur.execute("""
        SELECT re.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = %s
          AND rdv.dataset_version = %s
          AND dm.include_in_evaluation = TRUE
        ORDER BY ri.region_code, rit.authenticity_status
    """, (args.model, args.dataset))
    test_items = [{"id": str(r[0]), "embedding": parse_vec(r[1]), "region": r[2], "label": r[3]} for r in cur.fetchall()]

    # Load search items
    cur.execute("""
        SELECT re.reference_image_id, re.embedding, ri.region_code, rit.authenticity_status
        FROM reference_embeddings re
        JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
        JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        WHERE re.embedding_model_version = %s
          AND rdv.dataset_version = %s
          AND dm.include_in_search = TRUE
        ORDER BY ri.id
    """, (args.model, args.dataset))
    search_items = [{"id": str(r[0]), "embedding": parse_vec(r[1]), "region": r[2], "label": r[3]} for r in cur.fetchall()]

    print("=" * 70)
    print("  NEAREST NEIGHBOR INSPECTION")
    print("=" * 70)
    print(f"  Model: {args.model}")
    print(f"  Dataset: {args.dataset}")
    print(f"  Test items: {len(test_items)}")
    print(f"  Search items: {len(search_items)}")
    print(f"  K: {args.k}")

    results = []
    nn_agree = 0

    for t in test_items:
        # Find top-k neighbors in same region, excluding self
        sims = []
        for s in search_items:
            if s["id"] == t["id"]:
                continue
            if s["region"] != t["region"]:
                continue
            sim = cosine_sim(t["embedding"], s["embedding"])
            sims.append({"id": s["id"], "label": s["label"], "similarity": round(sim, 4)})

        sims.sort(key=lambda x: x["similarity"], reverse=True)
        top_k = sims[:args.k]
        nn_label = top_k[0]["label"] if top_k else "NONE"
        agrees = nn_label == t["label"]
        if agrees:
            nn_agree += 1

        print(f"\n  {t['region']} | {t['label']} | id={t['id'][:8]}...")
        for i, nb in enumerate(top_k):
            match = "=" if nb["label"] == t["label"] else "X"
            print(f"    [{match}] {i+1}. sim={nb['similarity']:.4f} | {nb['label']} | id={nb['id'][:8]}...")

        results.append({
            "reference_image_id": t["id"],
            "expected_label": t["label"],
            "region_code": t["region"],
            "nn_agrees": agrees,
            "neighbors": top_k,
        })

    total = len(test_items)
    print(f"\n  NN label agreement: {nn_agree}/{total} ({nn_agree/total:.1%})" if total else "")

    # Write JSON report
    if args.output:
        out_dir = os.path.join(args.output, args.dataset, args.model)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "neighbors.json")
        with open(out_path, "w") as f:
            json.dump({"model": args.model, "dataset": args.dataset, "k": args.k, "items": results}, f, indent=2)
        print(f"\n  Report written to: {out_path}")

    print(f"\n{'=' * 70}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
