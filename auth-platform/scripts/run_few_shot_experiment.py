#!/usr/bin/env python3
"""Phase 10 few-shot prototype-matching experiment runner.

Cross-tabulates few-shot inference strategies across embedding models, label
strategies, and shot counts on a governed reference dataset. Produces a
unified results bundle (summary.json + report.md + CSVs + run_config.json)
intended for downstream comparison with ``compare_few_shot_experiments.py``.

Diagnostic only on public texture data — not an authentication validator.

Usage:
  python scripts/run_few_shot_experiment.py \\
    --dataset external_leadata_v0.1.0 \\
    --model texture_baseline_v0.2.0 \\
    --model dinov2_base_frozen_v0.1.0 \\
    --label-strategy external_item_id \\
    --shots 1,3,5,10 \\
    --episodes 500
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ml"))

from experiments import few_shot  # noqa: E402

DB_DSN = os.environ.get(
    "AUTH_PLATFORM_DB_DSN",
    "postgresql://authplatform:authplatform@localhost:5432/authplatform",
)
DEFAULT_OUTPUT_DIR = ROOT.parent / "experiments" / "outputs" / "few-shot"
DEFAULT_SCORE_THRESHOLDS = "0.0,0.5,0.6,0.7,0.8,0.85,0.9"
DEFAULT_MARGIN_THRESHOLDS = "0.0,0.02,0.05,0.1,0.15"
ALL_STRATEGIES = [
    "nearest_neighbor",
    "top_k_mean",
    "prototype_centroid",
    "prototype_medoid",
    "prototype_centroid_with_abstention",
]

OBJECT_URI_PATTERN = re.compile(r"/raw/([^/]+)/")


def parse_vec(v) -> np.ndarray:
    if isinstance(v, list | np.ndarray):
        return np.asarray(v, dtype=np.float64)
    return np.array([float(x) for x in str(v).strip("[]").split(",")], dtype=np.float64)


def git_sha() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
        )
    except Exception:
        return "unknown"


def derive_external_item_id(object_uri: str) -> str:
    m = OBJECT_URI_PATTERN.search(object_uri or "")
    return m.group(1) if m else ""


def derive_sample_group(object_uri: str, species: str | None) -> str:
    """Sample group is the suffix of external_item_id after the species prefix."""
    eid = derive_external_item_id(object_uri)
    if not eid:
        return ""
    if species and eid.startswith(f"{species}_"):
        return eid[len(species) + 1 :]
    if "_" in eid:
        return eid.split("_", 1)[1]
    return eid


def load_records(
    dataset: str,
    model: str,
    db_dsn: str,
) -> list[dict]:
    """Load reference embeddings + label-derivation context from the DB.

    Returns a list of dicts with: embedding (np.ndarray), reference_image_id,
    reference_item_id, split, species, sample_group, external_item_id,
    object_uri, region_code.
    """
    conn = psycopg2.connect(db_dsn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            re.embedding,
            ri.id::text   AS reference_image_id,
            rit.id::text  AS reference_item_id,
            COALESCE(dm.split, 'all') AS split,
            rit.material  AS species,
            ri.object_uri AS object_uri,
            ri.region_code AS region_code
        FROM reference_embeddings re
        JOIN reference_images ri ON ri.id = re.reference_image_id
        JOIN reference_items rit ON rit.id = ri.reference_item_id
        LEFT JOIN reference_dataset_members dm ON dm.reference_image_id = ri.id
        LEFT JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
        WHERE re.embedding_model_version = %s
          AND rdv.dataset_version = %s
        ORDER BY ri.id
        """,
        (model, dataset),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    records: list[dict] = []
    for emb, ref_img_id, ref_item_id, split, species, object_uri, region_code in rows:
        records.append(
            {
                "embedding": parse_vec(emb),
                "reference_image_id": ref_img_id,
                "reference_item_id": ref_item_id,
                "split": split,
                "species": species or "",
                "external_item_id": ref_item_id,
                "sample_group": derive_sample_group(object_uri, species),
                "object_uri": object_uri,
                "region_code": region_code,
            }
        )
    return records


def run_cell(
    grouped: dict[str, list[np.ndarray]],
    *,
    embedding_model: str,
    label_strategy: str,
    K: int,
    strategies: list[str],
    episodes: int,
    query_per_class: int,
    ways: int | None,
    top_k_for_mean: int,
    score_thresholds: list[float],
    margin_thresholds: list[float],
    rng_seed: int,
) -> dict:
    """Run ``episodes`` episodes; apply each strategy to the same support/query."""
    rng = random.Random(rng_seed)
    per_episode: dict[str, list[float]] = {s: [] for s in strategies}
    per_episode_rows: list[dict] = []
    margins: dict[str, list[float]] = {s: [] for s in strategies}
    abstention_records: list[tuple[str, str, float, float]] = []
    skipped = 0

    for ep_idx in range(episodes):
        ep = few_shot.sample_episode(grouped, ways, K, query_per_class, rng)
        if ep is None:
            skipped += 1
            continue
        support, query = ep
        for strategy in strategies:
            acc, q_recs = few_shot.run_episode(
                support, query, strategy, top_k_for_mean=top_k_for_mean
            )
            per_episode[strategy].append(acc)
            for true_c, pred_c, t1, t2 in q_recs:
                margins[strategy].append(t1 - t2)
                per_episode_rows.append(
                    {
                        "embedding_model": embedding_model,
                        "label_strategy": label_strategy,
                        "K": K,
                        "strategy": strategy,
                        "episode_index": ep_idx,
                        "true_class": true_c,
                        "predicted_class": pred_c,
                        "top1_score": t1,
                        "top2_score": t2,
                        "correct": int(pred_c == true_c),
                    }
                )
                if strategy == "prototype_centroid_with_abstention":
                    abstention_records.append((true_c, pred_c, t1, t2))

    abstention_curve: list[dict] = []
    if abstention_records:
        abstention_curve = few_shot.evaluate_with_abstention_curve(
            abstention_records, score_thresholds, margin_thresholds
        )

    cell_summary = {
        "embedding_model": embedding_model,
        "label_strategy": label_strategy,
        "K": K,
        "episodes_planned": episodes,
        "episodes_skipped": skipped,
        "episodes_run": episodes - skipped,
        "strategies": {},
    }
    for strategy in strategies:
        stats = few_shot.support_set_variance(per_episode[strategy])
        margin_arr = np.asarray(margins[strategy], dtype=np.float64) if margins[strategy] else np.zeros(0)
        cell_summary["strategies"][strategy] = {
            "accuracy_mean": stats["mean"],
            "accuracy_std": stats["std"],
            "accuracy_p05": stats["p05"],
            "accuracy_p95": stats["p95"],
            "support_set_variance_p95": stats["p95"] - stats["p05"],
            "mean_top1_margin": float(margin_arr.mean()) if margin_arr.size else 0.0,
            "n_episodes": stats["n"],
        }

    return {
        "summary": cell_summary,
        "per_episode_rows": per_episode_rows,
        "abstention_curve": abstention_curve,
    }


def run_ood_block(
    in_grouped: dict[str, list[np.ndarray]],
    ood_records: list[dict],
    *,
    embedding_model: str,
    K: int,
    strategies: list[str],
    episodes: int,
    query_per_class_in: int,
    ways: int | None,
    top_k_for_mean: int,
    score_thresholds: list[float],
    margin_thresholds: list[float],
    rng_seed: int,
) -> dict:
    """OOD rejection diagnostic: in-domain support, OOD queries, abstain-or-reject rate."""
    rng = random.Random(rng_seed + 9001)
    ood_embeddings = [r["embedding"] for r in ood_records if r.get("embedding") is not None]
    if not ood_embeddings:
        return {"note": "no OOD embeddings under this model; skipped"}

    abst_records: dict[str, list[tuple[str, str, float, float]]] = {s: [] for s in strategies}
    samples_per_episode = max(1, query_per_class_in)
    for _ in range(episodes):
        ep = few_shot.sample_episode(in_grouped, ways, K, query_per_class_in, rng)
        if ep is None:
            continue
        support, _query = ep
        ood_sample = rng.sample(
            ood_embeddings, k=min(samples_per_episode, len(ood_embeddings))
        )
        for strategy in strategies:
            for q in ood_sample:
                fn = few_shot.STRATEGIES[strategy]
                res = fn(q, support, k=top_k_for_mean)
                abst_records[strategy].append(
                    ("__OOD__", res.predicted_class, res.top1_score, res.top2_score)
                )

    out_strategies: dict[str, dict] = {}
    for strategy in strategies:
        recs = abst_records[strategy]
        if not recs:
            out_strategies[strategy] = {"note": "no OOD queries scored"}
            continue
        curve = few_shot.evaluate_with_abstention_curve(
            recs, score_thresholds, margin_thresholds
        )
        # Treat "abstention" as OOD rejection. Higher threshold = more rejection.
        rejected = [r["abstention_rate"] for r in curve]
        out_strategies[strategy] = {
            "n_ood_queries_scored": len(recs),
            "ood_rejection_curve": curve,
            "ood_rejection_rate_mean": float(np.mean(rejected)) if rejected else 0.0,
            "ood_rejection_rate_max": float(np.max(rejected)) if rejected else 0.0,
        }
    return {"embedding_model": embedding_model, "K": K, "strategies": out_strategies}


def parse_csv_floats(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def parse_csv_ints(s: str) -> list[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def write_outputs(
    output_dir: Path,
    summary: dict,
    per_episode_rows: list[dict],
    abstention_curves: list[dict],
    run_config: dict,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "few_shot_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (output_dir / "run_config.json").write_text(json.dumps(run_config, indent=2, default=str))

    flat_rows: list[dict] = []
    for cell in summary["cells"]:
        for strategy, stats in cell["strategies"].items():
            row = {
                "embedding_model": cell["embedding_model"],
                "label_strategy": cell["label_strategy"],
                "K": cell["K"],
                "strategy": strategy,
                "episodes_run": cell["episodes_run"],
                **stats,
            }
            flat_rows.append(row)
    if flat_rows:
        with (output_dir / "few_shot_table.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(flat_rows[0].keys()))
            writer.writeheader()
            writer.writerows(flat_rows)

    if per_episode_rows:
        with (output_dir / "per_episode_results.csv").open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(per_episode_rows[0].keys()))
            writer.writeheader()
            writer.writerows(per_episode_rows)

    if abstention_curves:
        with (output_dir / "abstention_curves.csv").open("w", newline="") as fh:
            fields = list(abstention_curves[0].keys())
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(abstention_curves)

    report_lines: list[str] = []
    report_lines.append("# Phase 10 — Few-Shot Prototype Matching")
    report_lines.append("")
    report_lines.append("**Diagnostic only on public texture data. Not an authentication validator.**")
    report_lines.append("")
    report_lines.append(f"- Dataset: `{run_config['dataset']}`")
    report_lines.append(f"- Models: {', '.join(run_config['models'])}")
    report_lines.append(f"- Label strategy: `{run_config['label_strategy']}`")
    report_lines.append(f"- Split: `{run_config['split']}`")
    report_lines.append(f"- Episodes per cell: {run_config['episodes']}")
    report_lines.append(f"- Seed: {run_config['seed']}")
    report_lines.append(f"- Git SHA: `{run_config['git_sha']}`")
    report_lines.append("")
    report_lines.append("## Results")
    report_lines.append("")
    report_lines.append("| model | strategy | K | acc mean | acc std | p05 | p95 | margin | n |")
    report_lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in flat_rows:
        report_lines.append(
            "| {model} | {strat} | {K} | {acc:.4f} | {std:.4f} | {p05:.4f} | {p95:.4f} | {mar:.4f} | {n} |".format(
                model=row["embedding_model"],
                strat=row["strategy"],
                K=row["K"],
                acc=row["accuracy_mean"],
                std=row["accuracy_std"],
                p05=row["accuracy_p05"],
                p95=row["accuracy_p95"],
                mar=row["mean_top1_margin"],
                n=row["n_episodes"],
            )
        )
    (output_dir / "few_shot_report.md").write_text("\n".join(report_lines) + "\n")

    return output_dir


def print_console_table(summary: dict) -> None:
    headers = [
        "model", "strategy", "K",
        "acc_mean", "acc_std", "margin",
        "p95-p05", "n_episodes",
    ]
    print()
    print(" | ".join(f"{h:>16}" for h in headers))
    print("-" * (len(headers) * 19))
    for cell in summary["cells"]:
        for strategy, stats in cell["strategies"].items():
            print(
                " | ".join(
                    [
                        f"{cell['embedding_model']:>16}",
                        f"{strategy:>16}",
                        f"{cell['K']:>16}",
                        f"{stats['accuracy_mean']:>16.4f}",
                        f"{stats['accuracy_std']:>16.4f}",
                        f"{stats['mean_top1_margin']:>16.4f}",
                        f"{stats['support_set_variance_p95']:>16.4f}",
                        f"{stats['n_episodes']:>16}",
                    ]
                )
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--model", required=True, action="append", help="May be repeated")
    parser.add_argument(
        "--label-strategy", required=True,
        choices=["external_item_id", "sample_group", "species"],
    )
    parser.add_argument("--split", default="train")
    parser.add_argument("--shots", default="1,3,5,10")
    parser.add_argument("--ways", type=int, default=None)
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--query-per-class", type=int, default=5)
    parser.add_argument("--strategies", default="all")
    parser.add_argument("--top-k-for-mean", type=int, default=3)
    parser.add_argument("--score-threshold-sweep", default=DEFAULT_SCORE_THRESHOLDS)
    parser.add_argument("--margin-threshold-sweep", default=DEFAULT_MARGIN_THRESHOLDS)
    parser.add_argument("--ood-dataset", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--notes", default="")
    parser.add_argument("--db-dsn", default=DB_DSN)
    args = parser.parse_args()

    shots = parse_csv_ints(args.shots)
    score_thresholds = parse_csv_floats(args.score_threshold_sweep)
    margin_thresholds = parse_csv_floats(args.margin_threshold_sweep)
    strategies = ALL_STRATEGIES if args.strategies == "all" else [s.strip() for s in args.strategies.split(",")]
    for s in strategies:
        if s not in ALL_STRATEGIES:
            print(f"ERROR: unknown strategy {s!r}; known: {ALL_STRATEGIES}")
            return 2

    split_filter = None if args.split.lower() == "all" else {args.split}
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = str(uuid.uuid4())
    out_subdir = Path(args.output_dir) / f"{timestamp}_{args.dataset}_{args.label_strategy}"

    run_config = {
        "run_id": run_id,
        "timestamp": timestamp,
        "dataset": args.dataset,
        "ood_dataset": args.ood_dataset,
        "models": args.model,
        "label_strategy": args.label_strategy,
        "split": args.split,
        "shots": shots,
        "ways": args.ways,
        "episodes": args.episodes,
        "query_per_class": args.query_per_class,
        "strategies": strategies,
        "top_k_for_mean": args.top_k_for_mean,
        "score_threshold_sweep": score_thresholds,
        "margin_threshold_sweep": margin_thresholds,
        "seed": args.seed,
        "notes": args.notes,
        "git_sha": git_sha(),
    }

    cells: list[dict] = []
    all_per_episode: list[dict] = []
    all_abstention: list[dict] = []
    ood_blocks: list[dict] = []

    for model in args.model:
        records = load_records(args.dataset, model, args.db_dsn)
        if not records:
            print(f"  [{model}] no embeddings persisted under this model; skipping")
            continue
        try:
            grouped = few_shot.group_embeddings_by_label(
                records, args.label_strategy, split_filter=split_filter
            )
        except (ValueError, KeyError) as exc:
            print(f"  [{model}] grouping failed: {exc}; skipping")
            continue

        ood_grouped_records: list[dict] | None = None
        if args.ood_dataset:
            ood_recs = load_records(args.ood_dataset, model, args.db_dsn)
            ood_grouped_records = ood_recs if ood_recs else None

        for K in shots:
            print(f"  [{model}] K={K} label={args.label_strategy}: running...")
            cell = run_cell(
                grouped,
                embedding_model=model,
                label_strategy=args.label_strategy,
                K=K,
                strategies=strategies,
                episodes=args.episodes,
                query_per_class=args.query_per_class,
                ways=args.ways,
                top_k_for_mean=args.top_k_for_mean,
                score_thresholds=score_thresholds,
                margin_thresholds=margin_thresholds,
                rng_seed=args.seed + K,
            )
            cells.append(cell["summary"])
            all_per_episode.extend(cell["per_episode_rows"])
            for c in cell["abstention_curve"]:
                all_abstention.append(
                    {
                        "embedding_model": model,
                        "label_strategy": args.label_strategy,
                        "K": K,
                        **c,
                    }
                )
            if ood_grouped_records:
                ood_block = run_ood_block(
                    grouped,
                    ood_grouped_records,
                    embedding_model=model,
                    K=K,
                    strategies=strategies,
                    episodes=min(args.episodes, 100),
                    query_per_class_in=args.query_per_class,
                    ways=args.ways,
                    top_k_for_mean=args.top_k_for_mean,
                    score_thresholds=score_thresholds,
                    margin_thresholds=margin_thresholds,
                    rng_seed=args.seed + K,
                )
                ood_blocks.append(ood_block)

    summary = {
        "run_id": run_id,
        "timestamp": timestamp,
        "config": run_config,
        "cells": cells,
        "ood_blocks": ood_blocks,
        "diagnostic_only_on_public_texture_data": True,
    }

    write_outputs(out_subdir, summary, all_per_episode, all_abstention, run_config)
    print(f"\nWrote results to: {out_subdir}")
    print_console_table(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
