#!/usr/bin/env python3
"""Analyze embedding distributions for a model version.

Usage: python scripts/analyze_embeddings.py --model texture_baseline_v0.1.0 [--dataset synthetic_lv_monogram_v0.1.0] [--region EXTERIOR_CANVAS]
"""

import argparse
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
    return d / n if n > 0 else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="synthetic_lv_monogram_v0.1.0")
    parser.add_argument("--region", default=None)
    parser.add_argument("--split", default=None)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Build query
    conditions = ["re.embedding_model_version = %s"]
    params = [args.model]

    if args.region:
        conditions.append("ri.region_code = %s")
        params.append(args.region)
    if args.split:
        conditions.append("dm.split = %s")
        params.append(args.split)

    where = " AND ".join(conditions)

    cur.execute(f"""
        SELECT re.embedding, rit.authenticity_status, ri.region_code, dm.split
        FROM reference_embeddings re
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        LEFT JOIN reference_dataset_members dm ON dm.reference_image_id = ri.id
        LEFT JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        WHERE {where}
          AND (rdv.dataset_version = %s OR rdv.id IS NULL)
        ORDER BY ri.id
    """, params + [args.dataset])

    rows = cur.fetchall()
    if not rows:
        print(f"No embeddings found for model={args.model}, dataset={args.dataset}")
        sys.exit(0)

    embeddings = [parse_vec(r[0]) for r in rows]
    labels = [r[1] for r in rows]
    regions = [r[2] for r in rows]
    emb_matrix = np.array(embeddings)

    auth_idx = [i for i, label in enumerate(labels) if "AUTHENTIC" in label]
    counter_idx = [i for i, label in enumerate(labels) if "COUNTERFEIT" in label]

    norms = np.linalg.norm(emb_matrix, axis=1)

    print("=" * 60)
    print("  EMBEDDING DIAGNOSTICS")
    print("=" * 60)
    print(f"\n  Model:     {args.model}")
    print(f"  Dataset:   {args.dataset}")
    if args.region:
        print(f"  Region:    {args.region}")
    if args.split:
        print(f"  Split:     {args.split}")
    print(f"\n  Count:     {len(embeddings)}")
    print(f"  Dimension: {emb_matrix.shape[1]}")
    print(f"  Authentic: {len(auth_idx)}")
    print(f"  Counterfeit: {len(counter_idx)}")

    print("\n  Vector norms:")
    print(f"    Mean: {norms.mean():.4f}")
    print(f"    Min:  {norms.min():.4f}")
    print(f"    Max:  {norms.max():.4f}")

    # Pairwise similarities
    n = len(embeddings)
    if n > 1:
        all_sims = []
        aa_sims, cc_sims, ac_sims = [], [], []
        for i in range(n):
            for j in range(i + 1, n):
                sim = cosine_sim(embeddings[i], embeddings[j])
                all_sims.append(sim)
                li, lj = labels[i], labels[j]
                if "AUTHENTIC" in li and "AUTHENTIC" in lj:
                    aa_sims.append(sim)
                elif "COUNTERFEIT" in li and "COUNTERFEIT" in lj:
                    cc_sims.append(sim)
                else:
                    ac_sims.append(sim)

        print("\n  Pairwise cosine similarity:")
        print(f"    All pairs:             mean={np.mean(all_sims):.4f}, min={np.min(all_sims):.4f}, max={np.max(all_sims):.4f}")
        if aa_sims:
            print(f"    Authentic-Authentic:   mean={np.mean(aa_sims):.4f} (n={len(aa_sims)})")
        if cc_sims:
            print(f"    Counterfeit-Counterfeit: mean={np.mean(cc_sims):.4f} (n={len(cc_sims)})")
        if ac_sims:
            print(f"    Authentic-Counterfeit: mean={np.mean(ac_sims):.4f} (n={len(ac_sims)})")

        # Cluster separation
        if aa_sims and cc_sims and ac_sims:
            intra = (np.mean(aa_sims) + np.mean(cc_sims)) / 2
            inter = np.mean(ac_sims)
            separation = intra - inter
            print("\n  Cluster separation:")
            print(f"    Intra-class mean:  {intra:.4f}")
            print(f"    Inter-class mean:  {inter:.4f}")
            print(f"    Separation score:  {separation:.4f} (positive = good)")

        # Nearest-neighbor label agreement
        nn_agree = 0
        for i in range(n):
            best_sim = -1
            best_label = None
            for j in range(n):
                if i == j:
                    continue
                sim = cosine_sim(embeddings[i], embeddings[j])
                if sim > best_sim:
                    best_sim = sim
                    best_label = labels[j]
            if best_label == labels[i]:
                nn_agree += 1
        print(f"\n  Nearest-neighbor label agreement: {nn_agree}/{n} ({nn_agree/n:.1%})")

    # Region breakdown
    unique_regions = sorted(set(regions))
    if len(unique_regions) > 1:
        print("\n  By region:")
        for region in unique_regions:
            r_idx = [i for i, r in enumerate(regions) if r == region]
            r_auth = sum(1 for i in r_idx if "AUTHENTIC" in labels[i])
            r_counter = len(r_idx) - r_auth
            print(f"    {region}: {len(r_idx)} (auth={r_auth}, counter={r_counter})")

    print(f"\n{'=' * 60}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
