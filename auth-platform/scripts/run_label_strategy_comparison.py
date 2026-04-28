#!/usr/bin/env python3
"""Run label strategy comparison across multiple configs.

Compares how different label strategies affect learned embedding quality while
holding other variables constant.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/run_label_strategy_comparison.py --configs ../experiments/configs/label_strategy_comparison
  python scripts/run_label_strategy_comparison.py --configs ../experiments/configs/label_strategy_comparison --limit 100 --epochs 2
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Semantic meaning of each label strategy for reporting
STRATEGY_SEMANTICS = {
    "external_item_id": "Same sample group/item retrieval",
    "species": "Same species retrieval (broader material class)",
    "sample_group": "Same sample folder retrieval",
    "authenticity_status": "Same authenticity status",
    "region_code": "Same region code",
}


def main():
    parser = argparse.ArgumentParser(description="Run label strategy comparison")
    parser.add_argument("--configs", required=True, help="Directory or comma-separated config paths")
    parser.add_argument("--dataset", default=None, help="Override dataset")
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs")
    parser.add_argument("--limit", type=int, default=None, help="Limit images per split")
    parser.add_argument("--device", default="auto", help="Device: auto/cpu/mps/cuda")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir) if args.output_dir
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "label-strategy-comparison"
    )

    configs_path = Path(args.configs)
    if configs_path.is_dir():
        config_files = sorted(configs_path.glob("*.yaml")) + sorted(configs_path.glob("*.yml"))
    else:
        config_files = [Path(p.strip()) for p in args.configs.split(",")]

    if not config_files:
        print("No config files found.")
        sys.exit(1)

    print(f"Configs:  {len(config_files)}")
    print(f"Output:   {output_dir}")
    if args.epochs:
        print(f"Epochs:   {args.epochs} (override)")
    if args.limit:
        print(f"Limit:    {args.limit}")

    python = sys.executable
    results = []
    failures = []

    for i, config_path in enumerate(config_files):
        name = config_path.stem
        print(f"\n{'=' * 70}")
        print(f"  [{i + 1}/{len(config_files)}] {name}")
        print(f"{'=' * 70}")

        cmd = [
            python, "scripts/run_learned_metric_experiment.py",
            "--config", str(config_path),
            "--output-dir", str(output_dir),
            "--device", args.device,
        ]
        if args.dataset:
            cmd.extend(["--dataset", args.dataset])
        if args.epochs:
            cmd.extend(["--epochs", str(args.epochs)])
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])

        try:
            result = subprocess.run(
                cmd, capture_output=False, text=True,
                cwd=Path(__file__).parent.parent,
            )
            if result.returncode != 0:
                print(f"  FAILED (exit {result.returncode})")
                failures.append({"config": name, "error": f"exit {result.returncode}"})
                if args.fail_fast:
                    break
                continue
        except Exception as exc:
            print(f"  ERROR: {exc}")
            failures.append({"config": name, "error": str(exc)})
            if args.fail_fast:
                break
            continue

        # Find generated record
        records = sorted(output_dir.glob("*__experiment_record.json"), key=lambda p: p.stat().st_mtime)
        if records:
            rec = json.loads(records[-1].read_text())
            results.append(rec)
            em = rec.get("evaluation_metrics", {})
            if em:
                print(f"  Cluster sep: {em.get('cluster_separation', 'N/A')}")
                print(f"  NN agree:    {em.get('nn_agreement_rate', 'N/A')}")
        else:
            results.append({"config": name, "loss": "?", "label_strategy": "?", "evaluation_metrics": None})

    # Print comparison
    print(f"\n{'=' * 110}")
    print("  Label Strategy Comparison (diagnostic only)")
    print(f"{'=' * 110}")
    print(f"\n  {'Loss':<22} {'Labels':<20} {'Classes':>7} {'ClustSep':>10} {'NN Agree':>10} "
          f"{'R@1':>8} {'R@3':>8} {'Time':>8}")
    print(f"  {'-' * 100}")

    for rec in results:
        em = rec.get("evaluation_metrics", {})
        loss = rec.get("loss", "?")
        ls = rec.get("label_strategy", "?")
        nc = rec.get("n_classes", "?")
        if not em:
            print(f"  {loss:<22} {ls:<20} {str(nc):>7}  (no evaluation metrics)")
            continue
        print(f"  {loss:<22} {ls:<20} {str(nc):>7} "
              f"{em.get('cluster_separation', 0):>10.4f} "
              f"{em.get('nn_agreement_rate', 0):>9.1%} "
              f"{em.get('recall_at_1', 0):>8.4f} "
              f"{em.get('recall_at_3', 0):>8.4f} "
              f"{rec.get('training_time_seconds', ''):>7}s")

    # Save summary
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)

    summary = {
        "timestamp": now.isoformat(),
        "configs_run": len(config_files),
        "successes": len(results),
        "failures": failures,
        "results": [
            {
                **rec,
                "semantic_meaning": STRATEGY_SEMANTICS.get(rec.get("label_strategy", ""), ""),
            }
            for rec in results
        ],
        "notes": args.notes,
    }
    json_path = output_dir / "label_strategy_comparison_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    csv_path = output_dir / "label_strategy_comparison_table.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["loss", "label_strategy", "semantic_meaning", "n_classes",
                         "cluster_separation", "nn_agreement_rate", "recall_at_1",
                         "recall_at_3", "recall_at_5", "training_time_seconds"])
        for rec in results:
            em = rec.get("evaluation_metrics", {})
            writer.writerow([
                rec.get("loss", ""), rec.get("label_strategy", ""),
                STRATEGY_SEMANTICS.get(rec.get("label_strategy", ""), ""),
                rec.get("n_classes", ""),
                em.get("cluster_separation", ""), em.get("nn_agreement_rate", ""),
                em.get("recall_at_1", ""), em.get("recall_at_3", ""),
                em.get("recall_at_5", ""), rec.get("training_time_seconds", ""),
            ])

    md_lines = [
        "# Label Strategy Comparison Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> Results are diagnostic only. They do not prove authentication accuracy.",
        "",
        f"- Configs run: {len(config_files)}",
        f"- Successes: {len(results)}",
        f"- Failures: {len(failures)}",
        "",
    ]
    md_path = output_dir / "label_strategy_comparison_report.md"
    md_path.write_text("\n".join(md_lines) + "\n")

    print(f"\nSummary: {json_path}")
    print(f"CSV:     {csv_path}")
    print(f"Report:  {md_path}")

    if failures:
        print(f"\nWARNING: {len(failures)} config(s) failed:")
        for f_item in failures:
            print(f"  {f_item['config']}: {f_item['error']}")


if __name__ == "__main__":
    main()
