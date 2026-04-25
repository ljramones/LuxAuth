#!/usr/bin/env python3
"""Export 2D PCA projection of embeddings to CSV.

Usage: python scripts/export_embedding_projection.py --model texture_baseline_v0.1.0 [--output reports/projections]
"""

import argparse
import os
import sys

import numpy as np
import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def parse_vec(v):
    if isinstance(v, (list, np.ndarray)):
        return np.array(v, dtype=float)
    return np.array([float(x) for x in str(v).strip("[]").split(",")], dtype=float)


def pca_2d(matrix):
    """Simple 2-component PCA without sklearn dependency."""
    centered = matrix - matrix.mean(axis=0)
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Take top 2 components (eigh returns ascending order)
    top2 = eigenvectors[:, -2:][:, ::-1]
    return centered @ top2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="synthetic_lv_monogram_v0.1.0")
    parser.add_argument("--output", default="reports/projections")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    cur.execute("""
        SELECT re.reference_image_id, re.embedding, rit.authenticity_status,
               ri.region_code, COALESCE(dm.split, 'unknown')
        FROM reference_embeddings re
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        LEFT JOIN reference_dataset_members dm ON dm.reference_image_id = ri.id
        LEFT JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        WHERE re.embedding_model_version = %s
          AND (rdv.dataset_version = %s OR rdv.id IS NULL)
        ORDER BY ri.id
    """, (args.model, args.dataset))
    rows = cur.fetchall()

    if len(rows) < 2:
        print(f"Need at least 2 embeddings, got {len(rows)}")
        sys.exit(0)

    ids = [str(r[0]) for r in rows]
    embeddings = np.array([parse_vec(r[1]) for r in rows])
    labels = [r[2] for r in rows]
    regions = [r[3] for r in rows]
    splits = [r[4] for r in rows]

    projected = pca_2d(embeddings)

    out_dir = os.path.join(args.output, args.dataset, args.model)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "projection.csv")

    with open(out_path, "w") as f:
        f.write("reference_image_id,authenticity_status,region_code,split,x,y\n")
        for i in range(len(ids)):
            f.write(f"{ids[i]},{labels[i]},{regions[i]},{splits[i]},{projected[i,0]:.6f},{projected[i,1]:.6f}\n")

    print(f"Exported {len(ids)} embeddings to {out_path}")
    print(f"  Model: {args.model}")
    print(f"  Dataset: {args.dataset}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
