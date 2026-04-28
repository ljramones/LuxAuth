#!/usr/bin/env python3
"""Run augmentation and training-schedule comparison across multiple configs.

Compares augmentation profiles, optimizers, schedulers, and projection heads.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/run_augmentation_schedule_comparison.py --configs ../experiments/configs/augmentation_schedule_comparison
  python scripts/run_augmentation_schedule_comparison.py --configs ../experiments/configs/augmentation_schedule_comparison --limit 100 --epochs 2
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Run backbone comparison")
    parser.add_argument("--configs", required=True)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    output_dir = (
        Path(args.output_dir) if args.output_dir
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "augmentation-schedule-comparison"
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

        records = sorted(output_dir.glob("*__experiment_record.json"), key=lambda p: p.stat().st_mtime)
        if records:
            rec = json.loads(records[-1].read_text())
            results.append(rec)
            em = rec.get("evaluation_metrics", {})
            if em:
                print(f"  Cluster sep: {em.get('cluster_separation', 'N/A')}")
                print(f"  NN agree:    {em.get('nn_agreement_rate', 'N/A')}")
        else:
            results.append({"config": name, "evaluation_metrics": None})

    # Print comparison sorted by cluster separation
    valid = [r for r in results if r.get("evaluation_metrics")]
    valid.sort(key=lambda r: r["evaluation_metrics"].get("cluster_separation", 0), reverse=True)

    print(f"\n{'=' * 120}")
    print("  Augmentation/Schedule Comparison (diagnostic only)")
    print("  Baseline: texture_baseline_v0.2.0 cluster_sep=0.9418, NN_agree=100%")
    print(f"{'=' * 120}")
    print(f"\n  {'Aug':<8} {'Loss':<18} {'Opt':<6} {'Sched':<7} {'Ep':>3} "
          f"{'ClustSep':>10} {'NN Agree':>10} {'R@1':>8} {'Time':>8}")
    print(f"  {'-' * 85}")

    for rec in valid:
        em = rec["evaluation_metrics"]
        aug = rec.get("augmentation_profile", "?")
        opt_d = rec.get("optimizer", {})
        opt_name = opt_d.get("name", "adam") if isinstance(opt_d, dict) else "adam"
        sched_d = rec.get("scheduler", {})
        sched_name = sched_d.get("name", "none") if isinstance(sched_d, dict) else "none"
        print(f"  {aug:<8} "
              f"{rec.get('loss', '?'):<18} "
              f"{opt_name:<6} "
              f"{sched_name:<7} "
              f"{rec.get('epochs', ''):>3} "
              f"{em.get('cluster_separation', 0):>10.4f} "
              f"{em.get('nn_agreement_rate', 0):>9.1%} "
              f"{em.get('recall_at_1', 0):>8.4f} "
              f"{rec.get('training_time_seconds', ''):>7}s")

    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)

    summary = {
        "timestamp": now.isoformat(),
        "configs_run": len(config_files),
        "successes": len(results),
        "failures": failures,
        "results": results,
        "notes": args.notes,
    }
    json_path = output_dir / "augmentation_schedule_comparison_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    csv_path = output_dir / "augmentation_schedule_comparison_table.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["backbone", "freeze_backbone", "embedding_dim", "loss",
                         "total_params", "trainable_params", "frozen_params",
                         "cluster_separation", "nn_agreement_rate", "recall_at_1",
                         "recall_at_3", "recall_at_5", "training_time_seconds"])
        for rec in results:
            em = rec.get("evaluation_metrics", {})
            writer.writerow([
                rec.get("backbone", ""), rec.get("freeze_backbone", ""),
                rec.get("embedding_dim", ""), rec.get("loss", ""),
                rec.get("total_params", ""), rec.get("trainable_params", ""),
                rec.get("frozen_params", ""),
                em.get("cluster_separation", ""), em.get("nn_agreement_rate", ""),
                em.get("recall_at_1", ""), em.get("recall_at_3", ""),
                em.get("recall_at_5", ""), rec.get("training_time_seconds", ""),
            ])

    md_lines = [
        "# Augmentation/Schedule Comparison Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> Results are diagnostic only. They do not prove authentication accuracy.",
        "",
        f"- Configs run: {len(config_files)}",
        f"- Successes: {len(valid)}",
        f"- Failures: {len(failures)}",
        "",
    ]
    md_path = output_dir / "augmentation_schedule_comparison_report.md"
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
