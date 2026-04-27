"""Out-of-distribution scoring utilities for embedding experiments.

Provides multiple OOD scoring methods for comparing query embeddings against
a reference distribution. Methods range from simple (max similarity) to
statistical (Mahalanobis distance).

Results are diagnostic only — they do not prove authentication accuracy.
"""

from __future__ import annotations

import numpy as np


def cosine_similarities(query: np.ndarray, references: np.ndarray) -> np.ndarray:
    """Compute cosine similarities between a query and all references.

    Args:
        query: (D,) query embedding.
        references: (N, D) reference embeddings.

    Returns:
        (N,) array of cosine similarities.
    """
    q_norm = np.linalg.norm(query)
    r_norms = np.linalg.norm(references, axis=1)
    if q_norm == 0:
        return np.zeros(len(references))
    dots = references @ query
    denoms = r_norms * q_norm
    denoms = np.where(denoms > 0, denoms, 1.0)
    return dots / denoms


# ---------------------------------------------------------------------------
# A. Max similarity score
# ---------------------------------------------------------------------------

def max_similarity_score(query: np.ndarray, references: np.ndarray) -> dict:
    """Score based on maximum cosine similarity to any reference.

    Returns max_similarity and ood_score = 1 - max_similarity.
    """
    sims = cosine_similarities(query, references)
    max_sim = float(np.max(sims)) if len(sims) > 0 else 0.0
    return {
        "max_similarity": max_sim,
        "ood_score": 1.0 - max_sim,
    }


# ---------------------------------------------------------------------------
# B. Mean top-K similarity
# ---------------------------------------------------------------------------

def mean_topk_similarity(query: np.ndarray, references: np.ndarray, k: int = 5) -> dict:
    """Average of top-K cosine similarities.

    More robust than max alone — one accidental high neighbor is smoothed out.
    """
    sims = cosine_similarities(query, references)
    k = min(k, len(sims))
    if k == 0:
        return {"mean_topk": 0.0, "ood_score": 1.0, "k": 0}
    topk = np.sort(sims)[-k:]
    mean = float(np.mean(topk))
    return {
        "mean_topk": mean,
        "ood_score": 1.0 - mean,
        "k": k,
    }


# ---------------------------------------------------------------------------
# C. Similarity gap
# ---------------------------------------------------------------------------

def similarity_gap(query: np.ndarray, references: np.ndarray) -> dict:
    """Gap between top-1 and top-2 similarity.

    Low gap can indicate ambiguity — the query is roughly equidistant from
    its two closest references.
    """
    sims = cosine_similarities(query, references)
    sorted_sims = np.sort(sims)[::-1]
    top1 = float(sorted_sims[0]) if len(sorted_sims) > 0 else 0.0
    top2 = float(sorted_sims[1]) if len(sorted_sims) > 1 else 0.0
    # OOD score: low top1 or low gap both suggest OOD/ambiguity
    # Use 1 - top1 as the primary OOD signal (consistent with max_similarity)
    return {
        "top1": top1,
        "top2": top2,
        "gap": top1 - top2,
        "ood_score": 1.0 - top1,
    }


# ---------------------------------------------------------------------------
# D. kNN density score
# ---------------------------------------------------------------------------

def knn_density_score(query: np.ndarray, references: np.ndarray, k: int = 5) -> dict:
    """Mean similarity to k nearest neighbors as a density proxy.

    Higher density (higher mean similarity) = more likely in-distribution.
    """
    sims = cosine_similarities(query, references)
    k = min(k, len(sims))
    if k == 0:
        return {"knn_mean_sim": 0.0, "ood_score": 1.0, "k": 0}
    topk = np.sort(sims)[-k:]
    mean_sim = float(np.mean(topk))
    return {
        "knn_mean_sim": mean_sim,
        "ood_score": 1.0 - mean_sim,
        "k": k,
    }


# ---------------------------------------------------------------------------
# E. Mahalanobis distance
# ---------------------------------------------------------------------------

def mahalanobis_distance(
    query: np.ndarray,
    references: np.ndarray,
    shrinkage: float = 0.1,
) -> dict:
    """Mahalanobis distance from query to reference distribution.

    Uses covariance with diagonal shrinkage for numerical stability.

    Args:
        query: (D,) query embedding.
        references: (N, D) reference embeddings.
        shrinkage: Regularization weight toward diagonal covariance.

    Returns:
        Dict with mahalanobis_distance and ood_score (normalized).
    """
    if len(references) < 2:
        return {"mahalanobis_distance": float("inf"), "ood_score": 1.0}

    mean = np.mean(references, axis=0)
    diff = query - mean

    # Covariance with shrinkage
    cov = np.cov(references, rowvar=False)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]])
    diag = np.diag(np.diag(cov))
    cov_reg = (1.0 - shrinkage) * cov + shrinkage * diag

    try:
        cov_inv = np.linalg.inv(cov_reg)
    except np.linalg.LinAlgError:
        # Fall back to pseudo-inverse
        cov_inv = np.linalg.pinv(cov_reg)

    dist = float(np.sqrt(np.clip(diff @ cov_inv @ diff, 0, None)))

    # Normalize: compute distances for all references to get scale
    ref_diffs = references - mean
    ref_dists = []
    for rd in ref_diffs:
        d = float(np.sqrt(np.clip(rd @ cov_inv @ rd, 0, None)))
        ref_dists.append(d)
    ref_dists = np.array(ref_dists)
    ref_mean = float(np.mean(ref_dists)) if len(ref_dists) > 0 else 1.0
    ref_std = float(np.std(ref_dists)) if len(ref_dists) > 1 else 1.0

    # Z-score-style normalization
    z_score = (dist - ref_mean) / ref_std if ref_std > 0 else 0.0

    return {
        "mahalanobis_distance": dist,
        "z_score": z_score,
        "ref_mean_distance": ref_mean,
        "ref_std_distance": ref_std,
        "ood_score": min(1.0, max(0.0, z_score / 3.0)),  # rough [0,1] mapping
    }


# ---------------------------------------------------------------------------
# F. Local outlier factor approximation
# ---------------------------------------------------------------------------

def lof_score(
    query: np.ndarray,
    references: np.ndarray,
    k: int = 5,
) -> dict:
    """Simple LOF-style score using kNN density ratio.

    Compares the kNN density of the query to the average kNN density of its
    k nearest neighbors in the reference set. No scikit-learn required.

    LOF > 1 suggests the query is in a sparser region than its neighbors (OOD).
    LOF ~ 1 suggests similar density (in-distribution).
    """
    n = len(references)
    if n < 2 or k < 1:
        return {"lof": 1.0, "ood_score": 0.5}

    k = min(k, n - 1)

    # Query density: mean similarity to its k nearest refs
    q_sims = cosine_similarities(query, references)
    q_topk_idx = np.argsort(q_sims)[-k:]
    q_density = float(np.mean(q_sims[q_topk_idx]))

    if q_density <= 0:
        return {"lof": float("inf"), "ood_score": 1.0}

    # Neighbor densities: for each of query's k nearest refs, compute their
    # kNN density within the reference set
    neighbor_densities = []
    for idx in q_topk_idx:
        ref = references[idx]
        r_sims = cosine_similarities(ref, references)
        # Exclude self
        r_sims[idx] = -1.0
        r_topk = np.sort(r_sims)[-k:]
        neighbor_densities.append(float(np.mean(r_topk)))

    avg_neighbor_density = float(np.mean(neighbor_densities))
    lof_val = avg_neighbor_density / q_density if q_density > 0 else float("inf")

    # LOF > 1 means query is in sparser region
    ood = min(1.0, max(0.0, (lof_val - 1.0) / 0.5))  # rough [0,1] mapping

    return {
        "lof": lof_val,
        "query_density": q_density,
        "avg_neighbor_density": avg_neighbor_density,
        "ood_score": ood,
    }


# ---------------------------------------------------------------------------
# Score all methods
# ---------------------------------------------------------------------------

def score_query(
    query: np.ndarray,
    references: np.ndarray,
    k: int = 5,
) -> dict:
    """Run all OOD scoring methods on a single query.

    Returns a dict with results from each method.
    """
    return {
        "max_similarity": max_similarity_score(query, references),
        "mean_topk": mean_topk_similarity(query, references, k),
        "similarity_gap": similarity_gap(query, references),
        "knn_density": knn_density_score(query, references, k),
        "mahalanobis": mahalanobis_distance(query, references),
        "lof": lof_score(query, references, k),
    }


# ---------------------------------------------------------------------------
# AUROC (manual implementation, no sklearn)
# ---------------------------------------------------------------------------

def compute_auroc(scores_positive: list[float], scores_negative: list[float]) -> float:
    """Compute AUROC using the Mann-Whitney U statistic.

    Positive = in-distribution (lower OOD score expected).
    Negative = out-of-distribution (higher OOD score expected).

    AUROC measures the probability that a random OOD sample has a higher
    OOD score than a random in-distribution sample.
    """
    n_pos = len(scores_positive)
    n_neg = len(scores_negative)
    if n_pos == 0 or n_neg == 0:
        return 0.5

    # Count pairs where negative score > positive score
    count = 0
    ties = 0
    for sp in scores_positive:
        for sn in scores_negative:
            if sn > sp:
                count += 1
            elif sn == sp:
                ties += 1

    return (count + 0.5 * ties) / (n_pos * n_neg)


def threshold_sweep(
    id_scores: list[float],
    ood_scores: list[float],
    n_thresholds: int = 50,
) -> list[dict]:
    """Sweep thresholds over OOD scores and compute rates.

    At each threshold:
    - false_ood_rate: fraction of ID samples incorrectly flagged as OOD
    - missed_ood_rate: fraction of OOD samples not flagged
    """
    all_scores = sorted(set(id_scores + ood_scores))
    if len(all_scores) <= n_thresholds:
        thresholds = all_scores
    else:
        lo, hi = min(all_scores), max(all_scores)
        thresholds = [lo + (hi - lo) * i / (n_thresholds - 1) for i in range(n_thresholds)]

    n_id = len(id_scores)
    n_ood = len(ood_scores)
    results = []
    for t in thresholds:
        false_ood = sum(1 for s in id_scores if s >= t) / n_id if n_id > 0 else 0
        missed_ood = sum(1 for s in ood_scores if s < t) / n_ood if n_ood > 0 else 0
        results.append({
            "threshold": round(t, 6),
            "false_ood_rate": round(false_ood, 4),
            "missed_ood_rate": round(missed_ood, 4),
        })
    return results


def find_best_threshold(sweep_results: list[dict]) -> dict:
    """Find the threshold that minimizes sum of false_ood + missed_ood rates."""
    if not sweep_results:
        return {"threshold": 0.5, "false_ood_rate": 1.0, "missed_ood_rate": 1.0}
    return min(sweep_results, key=lambda r: r["false_ood_rate"] + r["missed_ood_rate"])
