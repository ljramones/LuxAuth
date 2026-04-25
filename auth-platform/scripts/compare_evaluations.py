#!/usr/bin/env python3
"""Compare evaluation runs across embedding models.

Usage: python scripts/compare_evaluations.py
"""

import json
import sys
import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def main():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    # Get latest evaluation for each embedding model
    cur.execute("""
        SELECT DISTINCT ON (embedding_model_version)
            id, evaluation_name, embedding_model_version, reference_dataset_version,
            threshold_profile, status, summary_json
        FROM evaluation_runs
        WHERE status = 'COMPLETED'
        ORDER BY embedding_model_version, started_at DESC
    """)
    cols = [desc[0] for desc in cur.description]
    runs = [dict(zip(cols, row)) for row in cur.fetchall()]

    if not runs:
        print("No completed evaluation runs found.")
        sys.exit(0)

    print("=" * 70)
    print("  EVALUATION COMPARISON")
    print("=" * 70)

    # Header
    models = [r["embedding_model_version"] for r in runs]
    header = f"{'Metric':<30}"
    for m in models:
        header += f" {m:>18}"
    print(f"\n{header}")
    print("-" * len(header))

    metrics_keys = [
        ("total_items", "Total items"),
        ("authentic_items", "Authentic items"),
        ("counterfeit_items", "Counterfeit items"),
        ("true_positive_count", "True positives"),
        ("true_negative_count", "True negatives"),
        ("false_positive_count", "False positives"),
        ("false_negative_count", "False negatives"),
        ("inconclusive_count", "Inconclusive"),
        ("expert_review_count", "Expert review"),
        ("authentic_recall", "Authentic recall"),
        ("counterfeit_recall", "Counterfeit recall"),
        ("false_positive_rate", "False positive rate"),
        ("false_negative_rate", "False negative rate"),
    ]

    for key, label in metrics_keys:
        row = f"{label:<30}"
        for r in runs:
            summary = r["summary_json"] if isinstance(r["summary_json"], dict) else json.loads(r["summary_json"] or "{}")
            val = summary.get(key, "N/A")
            if isinstance(val, float):
                row += f" {val:>17.2%}"
            else:
                row += f" {str(val):>18}"
        print(row)

    print(f"\n{'=' * 70}")
    for r in runs:
        print(f"  {r['embedding_model_version']}: {r['evaluation_name']}")
        print(f"    Profile: {r['threshold_profile']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
