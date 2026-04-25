#!/usr/bin/env python3
"""Print a human-readable evaluation report.

Usage:
  python scripts/print_evaluation_report.py                   # latest run
  python scripts/print_evaluation_report.py --run-id <uuid>   # specific run
"""

import argparse
import json
import sys

import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    if args.run_id:
        cur.execute("SELECT * FROM evaluation_runs WHERE id = %s", (args.run_id,))
    else:
        cur.execute("SELECT * FROM evaluation_runs ORDER BY started_at DESC LIMIT 1")

    cols = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if not row:
        print("No evaluation runs found.")
        sys.exit(0)

    run = dict(zip(cols, row))
    summary = run["summary_json"] if isinstance(run["summary_json"], dict) else json.loads(run["summary_json"] or "{}")

    print("=" * 60)
    print("  EVALUATION REPORT")
    print("=" * 60)
    print(f"\n  Run:       {run['evaluation_name']}")
    print(f"  ID:        {run['id']}")
    print(f"  Status:    {run['status']}")
    print(f"  Dataset:   {run['reference_dataset_version']}")
    print(f"  Embedding: {run['embedding_model_version']}")
    print(f"  Profile:   {run['threshold_profile']}")
    print(f"  Started:   {run['started_at']}")
    print(f"  Completed: {run['completed_at']}")

    print(f"\n{'─' * 60}")
    print("  SUMMARY")
    print(f"{'─' * 60}")
    print(f"  Total items:          {summary.get('total_items', 0)}")
    print(f"  Authentic items:      {summary.get('authentic_items', 0)}")
    print(f"  Counterfeit items:    {summary.get('counterfeit_items', 0)}")
    print(f"  True positives:       {summary.get('true_positive_count', 0)}")
    print(f"  True negatives:       {summary.get('true_negative_count', 0)}")
    print(f"  False positives:      {summary.get('false_positive_count', 0)}")
    print(f"  False negatives:      {summary.get('false_negative_count', 0)}")
    print(f"  Inconclusive:         {summary.get('inconclusive_count', 0)}")
    print(f"  Expert review:        {summary.get('expert_review_count', 0)}")
    print(f"\n  Authentic recall:     {summary.get('authentic_recall', 0):.2%}")
    print(f"  Counterfeit recall:   {summary.get('counterfeit_recall', 0):.2%}")
    print(f"  False positive rate:  {summary.get('false_positive_rate', 0):.2%}")
    print(f"  False negative rate:  {summary.get('false_negative_rate', 0):.2%}")
    print(f"  Inconclusive rate:    {summary.get('inconclusive_rate', 0):.2%}")
    print(f"  Expert review rate:   {summary.get('expert_review_rate', 0):.2%}")

    # Breakdown by region
    cur.execute("""
        SELECT region_code, result, count(*)
        FROM evaluation_items WHERE evaluation_run_id = %s
        GROUP BY region_code, result ORDER BY region_code, result
    """, (str(run["id"]),))
    region_rows = cur.fetchall()

    if region_rows:
        print(f"\n{'─' * 60}")
        print("  BREAKDOWN BY REGION")
        print(f"{'─' * 60}")
        current_region = None
        for region, result, count in region_rows:
            if region != current_region:
                print(f"\n  {region}:")
                current_region = region
            print(f"    {result}: {count}")

    # Worst cases
    for label, title in [("FALSE_POSITIVE", "FALSE POSITIVES"), ("FALSE_NEGATIVE", "FALSE NEGATIVES")]:
        cur.execute("""
            SELECT reference_image_id, region_code, expected_label, predicted_label,
                   authentic_similarity, counterfeit_similarity
            FROM evaluation_items WHERE evaluation_run_id = %s AND result = %s
            LIMIT 5
        """, (str(run["id"]), label))
        worst = cur.fetchall()
        if worst:
            print(f"\n{'─' * 60}")
            print(f"  TOP {title} (up to 5)")
            print(f"{'─' * 60}")
            for ref_id, region, expected, predicted, auth_sim, counter_sim in worst:
                print(f"  {region}: expected={expected}, predicted={predicted}, "
                      f"auth_sim={auth_sim:.4f}, counter_sim={counter_sim:.4f}")

    print(f"\n{'=' * 60}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
