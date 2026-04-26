"""Generate experiment reports."""

from pathlib import Path


def write_markdown_report(records: list[dict], output_path: str | Path) -> None:
    """Write a comparison markdown report from multiple experiment records."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Baseline Feature Comparison Report",
        "",
        f"**Dataset:** {records[0]['dataset_version'] if records else 'N/A'}",
        f"**Split:** {records[0].get('split_scope', 'all')}",
        "",
        "| Metric | " + " | ".join(r["feature_extractor"] for r in records) + " |",
        "|---" + "|---" * len(records) + "|",
    ]

    metric_keys = [
        ("dimension", "Dimension"),
        ("count", "Embeddings"),
        ("norm_mean", "Norm mean"),
        ("cluster_separation", "Cluster separation"),
        ("nn_agreement_rate", "NN agreement"),
        ("recall_at_1", "Recall@1"),
        ("recall_at_3", "Recall@3"),
        ("recall_at_5", "Recall@5"),
        ("same_label_mean", "Same-label sim"),
        ("diff_label_mean", "Diff-label sim"),
        ("pairwise_mean", "Pairwise mean"),
    ]

    for key, label in metric_keys:
        vals = []
        for r in records:
            v = r["metrics"].get(key, "N/A")
            if isinstance(v, float):
                vals.append(f"{v:.4f}")
            else:
                vals.append(str(v))
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    lines.extend([
        "",
        "---",
        "",
        "*Texture feature comparison — validates embedding behavior, not authentication accuracy.*",
    ])

    path.write_text("\n".join(lines) + "\n")


def print_comparison(records: list[dict]) -> None:
    """Print comparison table to console."""
    if not records:
        print("No records to compare.")
        return

    print(f"\n{'Metric':<25}", end="")
    for r in records:
        print(f" {r['feature_extractor']:>28}", end="")
    print()
    print("-" * (25 + 29 * len(records)))

    keys = [
        ("dimension", "Dimension"),
        ("count", "Embeddings"),
        ("norm_mean", "Norm mean"),
        ("cluster_separation", "Cluster separation"),
        ("nn_agreement_rate", "NN agreement"),
        ("recall_at_1", "Recall@1"),
        ("recall_at_3", "Recall@3"),
        ("recall_at_5", "Recall@5"),
        ("same_label_mean", "Same-label sim"),
        ("diff_label_mean", "Diff-label sim"),
    ]

    for key, label in keys:
        print(f"{label:<25}", end="")
        for r in records:
            v = r["metrics"].get(key, "N/A")
            if isinstance(v, float):
                print(f" {v:>28.4f}", end="")
            else:
                print(f" {str(v):>28}", end="")
        print()
    print()
