#!/usr/bin/env python3
"""Generate a consolidated diagnostic report for an external public dataset.

Runs evaluation, embedding analysis, nearest-neighbor inspection, and projection
export, then writes a consolidated markdown report.

Usage:
  python scripts/external_dataset_report.py --dataset external_fabricnet_v0.1.0 --model texture_baseline_v0.1.0
  python scripts/external_dataset_report.py --dataset external_leadata_v0.1.0 --model texture_baseline_v0.1.0 --overwrite
"""

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg2

DB_DSN = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
DEFAULT_OUTPUT_BASE = Path("reports/external-datasets")


def run_capture(cmd: list[str], label: str) -> tuple[bool, str]:
    """Run a command and capture stdout+stderr. Returns (success, output)."""
    print(f"  Running: {label}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    output = result.stdout
    if result.stderr:
        output += "\n" + result.stderr
    if result.returncode != 0:
        print(f"    FAILED (exit {result.returncode})")
    else:
        print("    OK")
    return result.returncode == 0, output


def get_dataset_info(cur, dataset_version: str, model_version: str = "") -> dict | None:
    """Fetch dataset metadata from DB."""
    cur.execute(
        "SELECT id, dataset_version, source_type, status, description FROM reference_dataset_versions WHERE dataset_version = %s",
        (dataset_version,),
    )
    row = cur.fetchone()
    if not row:
        return None
    ds_id = str(row[0])

    # Counts
    cur.execute("SELECT count(*) FROM reference_dataset_members WHERE dataset_version_id = %s", (ds_id,))
    total_images = cur.fetchone()[0]

    cur.execute(
        "SELECT split, count(*) FROM reference_dataset_members WHERE dataset_version_id = %s GROUP BY split ORDER BY split",
        (ds_id,),
    )
    splits = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute(
        """SELECT DISTINCT ri.region_code FROM reference_dataset_members dm
           JOIN reference_images ri ON ri.id = dm.reference_image_id
           WHERE dm.dataset_version_id = %s ORDER BY ri.region_code""",
        (ds_id,),
    )
    regions = [r[0] for r in cur.fetchall()]

    cur.execute(
        """SELECT DISTINCT rit.authenticity_status FROM reference_dataset_members dm
           JOIN reference_images ri ON ri.id = dm.reference_image_id
           JOIN reference_items rit ON rit.id = ri.reference_item_id
           WHERE dm.dataset_version_id = %s""",
        (ds_id,),
    )
    auth_statuses = [r[0] for r in cur.fetchall()]

    # Embedding count for selected model
    if model_version:
        cur.execute(
            """SELECT count(*) FROM reference_embeddings re
               JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
               WHERE dm.dataset_version_id = %s AND re.embedding_model_version = %s""",
            (ds_id, model_version),
        )
        selected_model_embeddings = cur.fetchone()[0]
    else:
        selected_model_embeddings = 0

    # Total embeddings across all models
    cur.execute(
        """SELECT count(*) FROM reference_embeddings re
           JOIN reference_dataset_members dm ON dm.reference_image_id = re.reference_image_id
           WHERE dm.dataset_version_id = %s""",
        (ds_id,),
    )
    total_embeddings = cur.fetchone()[0]

    return {
        "id": ds_id,
        "dataset_version": row[1],
        "source_type": row[2],
        "status": row[3],
        "description": row[4],
        "total_images": total_images,
        "splits": splits,
        "regions": regions,
        "auth_statuses": auth_statuses,
        "embedding_count": selected_model_embeddings,
        "total_embeddings_all_models": total_embeddings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate external dataset diagnostic report")
    parser.add_argument("--dataset", required=True, help="Dataset version (e.g., external_fabricnet_v0.1.0)")
    parser.add_argument("--model", required=True, help="Embedding model version (e.g., texture_baseline_v0.1.0)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: reports/external-datasets/{dataset}/{model})")
    parser.add_argument("--k", type=int, default=5, help="Top-K neighbors")
    parser.add_argument("--profile", default=None, help="Threshold profile name")
    parser.add_argument("--skip-evaluation", action="store_true")
    parser.add_argument("--skip-neighbors", action="store_true")
    parser.add_argument("--skip-projection", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output directory")
    args = parser.parse_args()

    # Validate dataset exists
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    ds_info = get_dataset_info(cur, args.dataset, args.model)
    if not ds_info:
        print(f"ERROR: Dataset not found: {args.dataset}")
        sys.exit(1)

    print(f"Dataset: {args.dataset} ({ds_info['total_images']} images, status={ds_info['status']})")
    print(f"Model:   {args.model}")

    if ds_info["embedding_count"] == 0:
        print(f"ERROR: No embeddings found for dataset {args.dataset}. Run reembed first.")
        sys.exit(1)

    cur.close()
    conn.close()

    # Output directory
    out_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_BASE / args.dataset / args.model
    if out_dir.exists() and not args.overwrite:
        print(f"ERROR: Output directory exists: {out_dir}")
        print("Use --overwrite to replace, or specify a different --output-dir.")
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    python = sys.executable
    steps: dict[str, tuple[bool, str]] = {}
    failures = []

    # 1. Evaluation
    if not args.skip_evaluation:
        eval_cmd = [python, "scripts/run_evaluation.py", "--dataset", args.dataset]
        if args.model:
            eval_cmd.extend(["--model", args.model])
        if args.profile:
            eval_cmd.extend(["--profile", args.profile])
        ok, output = run_capture(eval_cmd, "Evaluation")
        steps["evaluation"] = (ok, output)
        (out_dir / "evaluation-run.txt").write_text(output)
        if not ok:
            failures.append("evaluation")

        # Evaluation report
        report_cmd = [python, "scripts/print_evaluation_report.py"]
        ok2, output2 = run_capture(report_cmd, "Evaluation report")
        steps["evaluation_report"] = (ok2, output2)
        (out_dir / "evaluation-report.txt").write_text(output2)
    else:
        steps["evaluation"] = (True, "Skipped")
        steps["evaluation_report"] = (True, "Skipped")

    # 2. Embedding analysis
    analysis_cmd = [python, "scripts/analyze_embeddings.py", "--model", args.model, "--dataset", args.dataset]
    ok, output = run_capture(analysis_cmd, "Embedding analysis")
    steps["embedding_analysis"] = (ok, output)
    (out_dir / "embedding-analysis.txt").write_text(output)
    if not ok:
        failures.append("embedding_analysis")

    # 3. Nearest neighbors
    if not args.skip_neighbors:
        neighbors_cmd = [
            python, "scripts/inspect_neighbors.py",
            "--model", args.model, "--dataset", args.dataset,
            "--k", str(args.k), "--output", str(out_dir),
        ]
        ok, output = run_capture(neighbors_cmd, "Nearest neighbors")
        steps["neighbors"] = (ok, output)
        (out_dir / "neighbors-output.txt").write_text(output)
        if not ok:
            failures.append("neighbors")
    else:
        steps["neighbors"] = (True, "Skipped")

    # 4. Projection
    if not args.skip_projection:
        proj_cmd = [
            python, "scripts/export_embedding_projection.py",
            "--model", args.model, "--dataset", args.dataset,
            "--output", str(out_dir),
        ]
        ok, output = run_capture(proj_cmd, "Projection export")
        steps["projection"] = (ok, output)
        if not ok:
            failures.append("projection")
    else:
        steps["projection"] = (True, "Skipped")

    # 5. Write consolidated report
    report_lines = [
        "# External Dataset Diagnostic Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> This report validates pipeline and embedding behavior on public texture/material data.",
        "> It does **not** measure luxury authentication accuracy.",
        "> INCONCLUSIVE auth-style outcomes are expected for single-class PUBLIC_DATASET_CLASS external datasets.",
        "",
        "## Dataset",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Dataset version | `{ds_info['dataset_version']}` |",
        f"| Status | {ds_info['status']} |",
        f"| Source type | {ds_info['source_type']} |",
        f"| Total images | {ds_info['total_images']} |",
        f"| Embedding model | `{args.model}` |",
        f"| Embeddings (selected model) | {ds_info['embedding_count']} |",
        f"| Embeddings (all models) | {ds_info['total_embeddings_all_models']} |",
        f"| Region codes | {', '.join(ds_info['regions'])} |",
        f"| Label values | {', '.join(ds_info['auth_statuses'])} |",
        "",
        "### Splits",
        "",
        "| Split | Count |",
        "|---|---|",
    ]
    for split, count in sorted(ds_info["splits"].items()):
        report_lines.append(f"| {split} | {count} |")

    # Embedding coverage
    total = ds_info["total_images"]
    selected = ds_info["embedding_count"]
    pct = (selected / total * 100) if total else 0
    report_lines.extend([
        "",
        f"**Selected model coverage:** {selected}/{total} ({pct:.0f}%)",
    ])

    report_lines.extend([
        "",
        "## Step Results",
        "",
        "| Step | Status |",
        "|---|---|",
    ])
    for step_name, (ok, _) in steps.items():
        status = "PASS" if ok else "FAIL"
        report_lines.append(f"| {step_name} | {status} |")

    # Embed evaluation summary
    if steps["evaluation_report"][0] and steps["evaluation_report"][1] != "Skipped":
        report_lines.extend([
            "",
            "## Evaluation Report",
            "",
            "```",
            steps["evaluation_report"][1].strip(),
            "```",
        ])

    # Embed embedding analysis
    if steps["embedding_analysis"][0]:
        report_lines.extend([
            "",
            "## Embedding Analysis",
            "",
            "```",
            steps["embedding_analysis"][1].strip(),
            "```",
        ])

    # Neighbor summary
    if steps["neighbors"][0] and steps["neighbors"][1] != "Skipped":
        # Extract NN agreement line
        for line in steps["neighbors"][1].split("\n"):
            if "NN label agreement" in line:
                report_lines.extend(["", "## Nearest-Neighbor Summary", "", line.strip()])
                break
        report_lines.append("")
        report_lines.append("Full neighbor inspection: `neighbors.json`")

    # Projection
    if steps["projection"][0] and steps["projection"][1] != "Skipped":
        report_lines.extend([
            "",
            "## Projection",
            "",
            "PCA 2D projection exported. See `projection.csv` in this directory.",
        ])

    # Output files
    report_lines.extend([
        "",
        "## Generated Files",
        "",
        "| File | Content |",
        "|---|---|",
        "| `diagnostic-report.md` | This report |",
        "| `evaluation-run.txt` | Evaluation run output |",
        "| `evaluation-report.txt` | Formatted evaluation report |",
        "| `embedding-analysis.txt` | Embedding distribution diagnostics |",
        "| `neighbors-output.txt` | Neighbor inspection console output |",
        "| `neighbors.json` | Structured neighbor data (if generated) |",
        "| `projection.csv` | PCA 2D projection (if generated) |",
    ])

    # Limitations
    report_lines.extend([
        "",
        "## Limitations",
        "",
        "- Public datasets such as FabricNET and LeaData are **not** authentic-vs-counterfeit luxury datasets.",
        "- Auth-style evaluation metrics (TP, TN, FP, FN) are not meaningful for single-class external datasets.",
        "- Meaningful indicators are: ingestion success, split integrity, nearest-neighbor consistency, and embedding diagnostics.",
        "- This report does **not** measure luxury authentication accuracy.",
    ])

    if failures:
        report_lines.extend([
            "",
            "## Failures",
            "",
        ])
        for f in failures:
            report_lines.append(f"- **{f}** failed. See corresponding output file for details.")

    report_text = "\n".join(report_lines) + "\n"
    (out_dir / "diagnostic-report.md").write_text(report_text)

    print(f"\nReport written to: {out_dir}/diagnostic-report.md")
    print(f"Files: {', '.join(f.name for f in out_dir.iterdir())}")

    if failures:
        print(f"\nWARNING: {len(failures)} step(s) failed: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
