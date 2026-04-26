"""Compute experiment metrics from embeddings."""

import numpy as np


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    d = float(np.dot(a, b))
    n = float(np.linalg.norm(a) * np.linalg.norm(b))
    return d / n if n > 0 else 0.0


def compute_metrics(
    embeddings: list[list[float]],
    labels: list[str],
    regions: list[str] | None = None,
    max_pairs: int = 10000,
) -> dict:
    """Compute standard experiment metrics from embeddings and labels."""
    n = len(embeddings)
    if n == 0:
        return {"count": 0, "error": "no embeddings"}

    matrix = np.array(embeddings, dtype=float)
    norms = np.linalg.norm(matrix, axis=1)

    # Pairwise similarity stats
    same_sims: list[float] = []
    diff_sims: list[float] = []
    all_sims: list[float] = []
    pairs = 0

    for i in range(n):
        for j in range(i + 1, n):
            if pairs >= max_pairs:
                break
            sim = cosine_sim(matrix[i], matrix[j])
            all_sims.append(sim)
            if labels[i] == labels[j]:
                same_sims.append(sim)
            else:
                diff_sims.append(sim)
            pairs += 1
        if pairs >= max_pairs:
            break

    intra = float(np.mean(same_sims)) if same_sims else 0.0
    inter = float(np.mean(diff_sims)) if diff_sims else 0.0

    # NN agreement and recall@K
    nn_agree = 0
    recall_at = {1: 0, 3: 0, 5: 0}

    for i in range(n):
        sims_for_i = []
        for j in range(n):
            if i == j:
                continue
            sim = cosine_sim(matrix[i], matrix[j])
            sims_for_i.append((sim, labels[j]))
        sims_for_i.sort(key=lambda x: x[0], reverse=True)

        if sims_for_i and sims_for_i[0][1] == labels[i]:
            nn_agree += 1

        for k in [1, 3, 5]:
            top_k = sims_for_i[:k]
            if any(lbl == labels[i] for _, lbl in top_k):
                recall_at[k] += 1

    # Per-label stats
    unique_labels = sorted(set(labels))
    per_label = {}
    for lbl in unique_labels:
        idxs = [i for i, lab in enumerate(labels) if lab == lbl]
        per_label[lbl] = {"count": len(idxs)}

    # Per-region stats
    per_region = {}
    if regions:
        unique_regions = sorted(set(regions))
        for reg in unique_regions:
            idxs = [i for i, r in enumerate(regions) if r == reg]
            per_region[reg] = {"count": len(idxs)}

    return {
        "count": n,
        "dimension": matrix.shape[1],
        "norm_mean": round(float(norms.mean()), 4),
        "norm_min": round(float(norms.min()), 4),
        "norm_max": round(float(norms.max()), 4),
        "pairwise_mean": round(float(np.mean(all_sims)), 4) if all_sims else 0.0,
        "same_label_mean": round(intra, 4),
        "diff_label_mean": round(inter, 4),
        "cluster_separation": round(intra - inter, 4),
        "nn_agreement": nn_agree,
        "nn_agreement_rate": round(nn_agree / n, 4) if n > 0 else 0.0,
        "recall_at_1": round(recall_at[1] / n, 4) if n > 0 else 0.0,
        "recall_at_3": round(recall_at[3] / n, 4) if n > 0 else 0.0,
        "recall_at_5": round(recall_at[5] / n, 4) if n > 0 else 0.0,
        "pairs_sampled": pairs,
        "unique_labels": unique_labels,
        "per_label": per_label,
        "per_region": per_region,
    }
