"""Run a preprocessing comparison experiment.

Given a governed dataset and feature extractor, applies each preprocessing
strategy, computes embeddings, and evaluates embedding metrics.

Results are diagnostic only — they do not prove authentication accuracy.
"""

import time

import numpy as np

from experiments.feature_extractors import EXTRACTORS
from experiments.metrics import compute_metrics
from experiments.preprocessing import STRATEGIES


def aggregate_embeddings(embeddings: list[list[float]]) -> list[float]:
    """Average multiple embeddings and L2-normalize the result."""
    if not embeddings:
        return []
    if len(embeddings) == 1:
        return embeddings[0]
    arr = np.array(embeddings, dtype=float)
    mean = arr.mean(axis=0)
    norm = float(np.linalg.norm(mean))
    if norm > 0:
        mean = mean / norm
    return mean.tolist()


def run_strategy(
    strategy_name: str,
    images: list[bytes],
    labels: list[str],
    regions: list[str],
    extractor_name: str = "texture_baseline_v0.2.0",
    progress_every: int = 50,
) -> dict:
    """Run a single preprocessing strategy across all images.

    Returns a dict with strategy name, metrics, timing, and metadata.
    """
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES.keys())}")
    if extractor_name not in EXTRACTORS:
        raise ValueError(f"Unknown extractor: {extractor_name}. Available: {list(EXTRACTORS.keys())}")

    strategy_fn = STRATEGIES[strategy_name]
    extractor_fn = EXTRACTORS[extractor_name]

    n = len(images)
    embeddings = []
    t0 = time.monotonic()

    for i, img_bytes in enumerate(images):
        preprocessed = strategy_fn(img_bytes)
        # Embed each preprocessed image and aggregate
        sub_embeddings = [extractor_fn(p) for p in preprocessed]
        embedding = aggregate_embeddings(sub_embeddings)
        embeddings.append(embedding)

        done = i + 1
        if progress_every > 0 and (done % progress_every == 0 or done == n):
            elapsed_so_far = time.monotonic() - t0
            rate = done / elapsed_so_far if elapsed_so_far > 0 else 0
            eta = (n - done) / rate if rate > 0 else 0
            print(f"    [{done}/{n}] {elapsed_so_far:.1f}s elapsed, "
                  f"{rate:.1f} img/s, ~{eta:.0f}s remaining")

    elapsed = time.monotonic() - t0
    dim = len(embeddings[0]) if embeddings else 0

    metrics = compute_metrics(embeddings, labels, regions)

    return {
        "strategy": strategy_name,
        "extractor": extractor_name,
        "image_count": len(images),
        "embedding_dimension": dim,
        "runtime_seconds": round(elapsed, 2),
        "metrics": metrics,
    }


def run_all_strategies(
    images: list[bytes],
    labels: list[str],
    regions: list[str],
    extractor_name: str = "texture_baseline_v0.2.0",
    strategy_names: list[str] | None = None,
    progress_every: int = 50,
) -> list[dict]:
    """Run all (or selected) preprocessing strategies and return results."""
    names = strategy_names or list(STRATEGIES.keys())
    total_strategies = len(names)
    results = []
    t_total = time.monotonic()

    for si, name in enumerate(names):
        print(f"\n  [{si + 1}/{total_strategies}] Strategy: {name}")
        result = run_strategy(name, images, labels, regions, extractor_name, progress_every)
        m = result["metrics"]
        print(f"    Done: dim={result['embedding_dimension']}, "
              f"cluster_sep={m.get('cluster_separation', 'N/A')}, "
              f"nn_agree={m.get('nn_agreement_rate', 'N/A')}, "
              f"time={result['runtime_seconds']}s")
        results.append(result)

    total_elapsed = time.monotonic() - t_total
    print(f"\n  All strategies complete in {total_elapsed:.1f}s")
    return results


def format_comparison_table(results: list[dict]) -> str:
    """Format results as a markdown comparison table."""
    if not results:
        return "No results."

    headers = [
        "Strategy", "Dim", "Count", "Norm mean", "Cluster sep",
        "NN agree", "R@1", "R@3", "R@5",
        "Same-label", "Diff-label", "Time (s)",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]

    for r in results:
        m = r["metrics"]
        row = [
            r["strategy"],
            str(r["embedding_dimension"]),
            str(m.get("count", "")),
            f"{m.get('norm_mean', 0):.4f}",
            f"{m.get('cluster_separation', 0):.4f}",
            f"{m.get('nn_agreement_rate', 0):.1%}",
            f"{m.get('recall_at_1', 0):.4f}",
            f"{m.get('recall_at_3', 0):.4f}",
            f"{m.get('recall_at_5', 0):.4f}",
            f"{m.get('same_label_mean', 0):.4f}",
            f"{m.get('diff_label_mean', 0):.4f}",
            f"{r.get('runtime_seconds', '')}",
        ]
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def print_comparison_table(results: list[dict]) -> None:
    """Print a fixed-width comparison table to stdout."""
    if not results:
        print("No results.")
        return

    print(f"\n{'Strategy':<28} {'Dim':>5} {'ClustSep':>10} {'NN Agree':>10} "
          f"{'R@1':>8} {'R@3':>8} {'R@5':>8} {'Time':>7}")
    print("-" * 100)

    for r in results:
        m = r["metrics"]
        print(f"{r['strategy']:<28} {r['embedding_dimension']:>5} "
              f"{m.get('cluster_separation', 0):>10.4f} "
              f"{m.get('nn_agreement_rate', 0):>9.1%} "
              f"{m.get('recall_at_1', 0):>8.4f} "
              f"{m.get('recall_at_3', 0):>8.4f} "
              f"{m.get('recall_at_5', 0):>8.4f} "
              f"{r.get('runtime_seconds', 0):>6.1f}s")
    print()
