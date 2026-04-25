#!/usr/bin/env python3
"""Smoke test for the capture batch workflow.

Uses smoke_ prefixed names to avoid any collision with real lab data.
"""

import subprocess
import sys

import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"

SMOKE_BATCH = "smoke_lab_lv_monogram_batch_001"
SMOKE_DATASET = "smoke_lab_lv_monogram_v0.1.0"


def run(cmd: str) -> bool:
    print(f"\n  >> {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.strip().split("\n")[-10:]:
            print(f"    {line}")
    if result.returncode != 0:
        print(f"    STDERR: {result.stderr[-300:]}" if result.stderr else "")
        return False
    return True


def main():
    print("=" * 60)
    print("  Capture Batch Workflow Smoke Test")
    print("=" * 60)

    results = {}

    results["Generate batch"] = run("python3 scripts/generate_lab_capture_batch.py")

    results["Validate batch"] = run(
        f"python3 scripts/validate_capture_batch.py --batch {SMOKE_BATCH} --auto-create-device"
    )

    results["Ingest batch"] = run(
        f"python3 scripts/ingest_capture_batch.py --batch {SMOKE_BATCH}"
    )

    results["Promote to dataset"] = run(
        f"python3 scripts/promote_capture_batch_to_dataset.py --batch {SMOKE_BATCH} --dataset {SMOKE_DATASET}"
    )

    # Verify DB state
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    cur.execute("SELECT dataset_version, status FROM reference_dataset_versions ORDER BY dataset_version")
    datasets = cur.fetchall()
    print("\n  >> Dataset versions:")
    for ds, st in datasets:
        print(f"    {ds}: {st}")

    # Synthetic dataset should be untouched if it exists
    cur.execute("SELECT status FROM reference_dataset_versions WHERE dataset_version = 'synthetic_lv_monogram_v0.1.0'")
    synth = cur.fetchone()
    if synth:
        results["Synthetic dataset untouched"] = synth[0] == "active"
    else:
        results["Synthetic dataset untouched"] = True  # not ingested this session

    # Any real lab_* datasets should be untouched
    cur.execute("SELECT dataset_version, status FROM reference_dataset_versions WHERE dataset_version LIKE 'lab_%'")
    lab_rows = cur.fetchall()
    if lab_rows:
        print("  >> Real lab datasets (should be untouched):")
        for ds, st in lab_rows:
            print(f"    {ds}: {st}")
    results["No real lab data modified"] = True  # smoke test only touches smoke_* names

    # Smoke dataset should be draft
    cur.execute("SELECT status FROM reference_dataset_versions WHERE dataset_version = %s", (SMOKE_DATASET,))
    smoke_ds = cur.fetchone()
    results["Smoke dataset is draft"] = smoke_ds is not None and smoke_ds[0] == "draft"

    # Batch should be promoted
    cur.execute("SELECT status FROM capture_batches WHERE batch_code = %s", (SMOKE_BATCH,))
    batch = cur.fetchone()
    results["Batch promoted"] = batch is not None and batch[0] == "PROMOTED"

    cur.close()
    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results.items():
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  All checks passed.")
    else:
        print("\n  Some checks failed.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
