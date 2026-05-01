#!/usr/bin/env python3
"""Cross-tabulate Phase 10 few-shot experiment results.

Loads one or more ``few_shot_summary.json`` files (or auto-discovers the
``--latest N`` most recent ones) and prints a markdown-style comparison
report highlighting:

  - Best (model, strategy) combination per K
  - Best K per (model, strategy) combination — i.e., where the
    support-set stabilization curve plateaus
  - Diminishing-returns point: smallest K where (acc_{K+next} - acc_K) < 0.02
  - Most stable K per model (minimum p95-p05 spread)
  - Best abstention threshold: highest accuracy with abstention_rate < 0.3

Diagnostic only on public texture data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT.parent / "experiments" / "outputs" / "few-shot"


def discover_latest(n: int, root: Path) -> list[Path]:
    if not root.exists():
        return []
    candidates = sorted(
        (p for p in root.iterdir() if p.is_dir() and (p / "few_shot_summary.json").exists()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [p / "few_shot_summary.json" for p in candidates[:n]]


def load_summaries(paths: list[Path]) -> list[dict]:
    out = []
    for p in paths:
        with p.open() as fh:
            data = json.load(fh)
        data["__source__"] = str(p)
        out.append(data)
    return out


def collect_cells(summaries: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for s in summaries:
        for cell in s.get("cells", []):
            for strategy, stats in cell.get("strategies", {}).items():
                rows.append(
                    {
                        "source": s.get("__source__", ""),
                        "embedding_model": cell["embedding_model"],
                        "label_strategy": cell["label_strategy"],
                        "K": cell["K"],
                        "strategy": strategy,
                        **stats,
                    }
                )
    return rows


def best_per_K(rows: list[dict]) -> list[str]:
    by_label: dict[str, dict[int, dict]] = {}
    for r in rows:
        by_label.setdefault(r["label_strategy"], {}).setdefault(r["K"], None)
        cur = by_label[r["label_strategy"]][r["K"]]
        if cur is None or r["accuracy_mean"] > cur["accuracy_mean"]:
            by_label[r["label_strategy"]][r["K"]] = r

    out = ["## Best (model, strategy) per K", ""]
    out.append("| label_strategy | K | model | strategy | acc mean | acc std | p95-p05 |")
    out.append("|---|---:|---|---|---:|---:|---:|")
    for lbl in sorted(by_label):
        for K in sorted(by_label[lbl]):
            r = by_label[lbl][K]
            out.append(
                f"| {lbl} | {K} | {r['embedding_model']} | {r['strategy']} "
                f"| {r['accuracy_mean']:.4f} | {r['accuracy_std']:.4f} "
                f"| {r['support_set_variance_p95']:.4f} |"
            )
    return out


def diminishing_returns(rows: list[dict], delta: float = 0.02) -> list[str]:
    grouped: dict[tuple, list[dict]] = {}
    for r in rows:
        grouped.setdefault((r["label_strategy"], r["embedding_model"], r["strategy"]), []).append(r)

    out = ["## Diminishing returns point (smallest K where next-K gain < 0.02)", ""]
    out.append("| label_strategy | model | strategy | K* | acc at K* | acc at next K |")
    out.append("|---|---|---|---:|---:|---:|")
    for (lbl, model, strategy), group in sorted(grouped.items()):
        ordered = sorted(group, key=lambda r: r["K"])
        marker = None
        for i in range(len(ordered) - 1):
            if (ordered[i + 1]["accuracy_mean"] - ordered[i]["accuracy_mean"]) < delta:
                marker = (ordered[i], ordered[i + 1])
                break
        if marker is None:
            continue
        a, b = marker
        out.append(
            f"| {lbl} | {model} | {strategy} | {a['K']} "
            f"| {a['accuracy_mean']:.4f} | {b['accuracy_mean']:.4f} |"
        )
    return out


def most_stable_K(rows: list[dict]) -> list[str]:
    best: dict[tuple, dict] = {}
    for r in rows:
        key = (r["label_strategy"], r["embedding_model"], r["strategy"])
        cur = best.get(key)
        if cur is None or r["support_set_variance_p95"] < cur["support_set_variance_p95"]:
            best[key] = r
    out = ["## Most stable K per (model, strategy) (minimum p95-p05)", ""]
    out.append("| label_strategy | model | strategy | K | p95-p05 | acc mean |")
    out.append("|---|---|---|---:|---:|---:|")
    for (lbl, model, strategy), r in sorted(best.items()):
        out.append(
            f"| {lbl} | {model} | {strategy} | {r['K']} "
            f"| {r['support_set_variance_p95']:.4f} | {r['accuracy_mean']:.4f} |"
        )
    return out


def best_abstention_threshold(summaries: list[dict], abstention_max: float = 0.3) -> list[str]:
    """For each (model, K) cell, find the threshold pair maximizing accuracy
    among non-abstained queries while keeping abstention_rate < abstention_max."""
    out = ["## Best abstention threshold per (model, K) — abstention_rate < 0.30", ""]
    out.append("| model | K | label_strategy | score_thr | margin_thr | acc | abst rate |")
    out.append("|---|---:|---|---:|---:|---:|---:|")

    for s in summaries:
        # The summary doesn't carry the curve directly; we look it up from
        # abstention_curves.csv that sits next to the summary file.
        source = s.get("__source__")
        if not source:
            continue
        csv_path = Path(source).parent / "abstention_curves.csv"
        if not csv_path.exists():
            continue
        import csv as _csv

        with csv_path.open() as fh:
            reader = _csv.DictReader(fh)
            curves: dict[tuple, list[dict]] = {}
            for row in reader:
                key = (row["embedding_model"], row["label_strategy"], int(row["K"]))
                curves.setdefault(key, []).append(row)

        for key, rows in curves.items():
            kept = [
                r
                for r in rows
                if float(r["abstention_rate"]) < abstention_max
            ]
            if not kept:
                continue
            best = max(kept, key=lambda r: float(r["accuracy_after_abstention"]))
            out.append(
                f"| {key[0]} | {key[2]} | {key[1]} "
                f"| {float(best['score_threshold']):.2f} | {float(best['margin_threshold']):.2f} "
                f"| {float(best['accuracy_after_abstention']):.4f} | {float(best['abstention_rate']):.4f} |"
            )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inputs", nargs="*", default=[], help="Paths to few_shot_summary.json files")
    parser.add_argument("--latest", type=int, default=None, help="Auto-discover N most recent summaries")
    parser.add_argument("--output", default=None, help="Write report to file (default: stdout)")
    parser.add_argument("--root", default=str(DEFAULT_OUTPUT_DIR), help="Root for --latest discovery")
    args = parser.parse_args()

    paths: list[Path] = [Path(p) for p in args.inputs]
    if args.latest:
        paths.extend(discover_latest(args.latest, Path(args.root)))
    paths = list(dict.fromkeys(paths))  # dedupe, preserve order

    if not paths:
        print("No few_shot_summary.json paths supplied. Use --inputs or --latest N.")
        return 2

    summaries = load_summaries(paths)
    rows = collect_cells(summaries)
    if not rows:
        print("No comparable cells found in the provided summaries.")
        return 1

    out_lines: list[str] = []
    out_lines.append("# Phase 10 — Few-Shot Comparison")
    out_lines.append("")
    out_lines.append(f"_Sources ({len(paths)}):_  ")
    for p in paths:
        out_lines.append(f"- `{p}`")
    out_lines.append("")
    out_lines.append("**Diagnostic only on public texture data.**")
    out_lines.append("")
    out_lines.extend(best_per_K(rows))
    out_lines.append("")
    out_lines.extend(diminishing_returns(rows))
    out_lines.append("")
    out_lines.extend(most_stable_K(rows))
    out_lines.append("")
    out_lines.extend(best_abstention_threshold(summaries))
    out_lines.append("")

    text = "\n".join(out_lines) + "\n"
    if args.output:
        Path(args.output).write_text(text)
        print(f"Wrote {args.output}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
