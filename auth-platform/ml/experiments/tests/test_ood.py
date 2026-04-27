"""Tests for OOD scoring utilities."""

import numpy as np

from experiments.ood import (
    compute_auroc,
    cosine_similarities,
    find_best_threshold,
    knn_density_score,
    lof_score,
    mahalanobis_distance,
    max_similarity_score,
    mean_topk_similarity,
    score_query,
    similarity_gap,
    threshold_sweep,
)


def _unit_vec(dim: int, seed: int = 0) -> np.ndarray:
    rng = np.random.RandomState(seed)
    v = rng.randn(dim)
    return v / np.linalg.norm(v)


def _ref_matrix(n: int, dim: int, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    m = rng.randn(n, dim)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / norms


class TestCosineSimilarities:
    def test_self_similarity(self):
        v = _unit_vec(128)
        refs = v.reshape(1, -1)
        sims = cosine_similarities(v, refs)
        assert abs(sims[0] - 1.0) < 1e-6

    def test_orthogonal(self):
        v1 = np.array([1.0, 0.0])
        v2 = np.array([0.0, 1.0])
        sims = cosine_similarities(v1, v2.reshape(1, -1))
        assert abs(sims[0]) < 1e-6

    def test_zero_query(self):
        q = np.zeros(10)
        refs = _ref_matrix(5, 10)
        sims = cosine_similarities(q, refs)
        assert all(s == 0.0 for s in sims)


class TestMaxSimilarity:
    def test_basic(self):
        q = _unit_vec(64, seed=0)
        refs = _ref_matrix(20, 64)
        result = max_similarity_score(q, refs)
        assert "max_similarity" in result
        assert "ood_score" in result
        assert abs(result["max_similarity"] + result["ood_score"] - 1.0) < 1e-6

    def test_self_in_refs(self):
        q = _unit_vec(32)
        refs = np.vstack([_ref_matrix(5, 32), q.reshape(1, -1)])
        result = max_similarity_score(q, refs)
        assert result["max_similarity"] > 0.99
        assert result["ood_score"] < 0.01


class TestMeanTopK:
    def test_k_larger_than_refs(self):
        q = _unit_vec(32)
        refs = _ref_matrix(3, 32)
        result = mean_topk_similarity(q, refs, k=10)
        assert result["k"] == 3

    def test_returns_expected_keys(self):
        q = _unit_vec(32)
        refs = _ref_matrix(10, 32)
        result = mean_topk_similarity(q, refs, k=5)
        assert "mean_topk" in result
        assert "ood_score" in result
        assert "k" in result


class TestSimilarityGap:
    def test_basic(self):
        q = _unit_vec(32)
        refs = _ref_matrix(10, 32)
        result = similarity_gap(q, refs)
        assert result["top1"] >= result["top2"]
        assert result["gap"] >= 0

    def test_single_ref(self):
        q = _unit_vec(32)
        refs = _ref_matrix(1, 32)
        result = similarity_gap(q, refs)
        assert result["top2"] == 0.0


class TestKnnDensity:
    def test_basic(self):
        q = _unit_vec(64)
        refs = _ref_matrix(20, 64)
        result = knn_density_score(q, refs, k=5)
        assert 0 <= result["ood_score"] <= 1.0
        assert result["k"] == 5


class TestMahalanobis:
    def test_in_distribution(self):
        refs = _ref_matrix(50, 32, seed=42)
        q = refs[0]  # query is in the reference set
        result = mahalanobis_distance(q, refs)
        assert result["mahalanobis_distance"] < float("inf")
        assert "z_score" in result

    def test_singular_covariance(self):
        # Very small dim, many refs — shouldn't crash
        refs = _ref_matrix(5, 3, seed=42)
        q = _unit_vec(3, seed=99)
        result = mahalanobis_distance(q, refs)
        assert result["mahalanobis_distance"] < float("inf")

    def test_too_few_refs(self):
        q = _unit_vec(32)
        refs = _ref_matrix(1, 32)
        result = mahalanobis_distance(q, refs)
        assert result["mahalanobis_distance"] == float("inf")
        assert result["ood_score"] == 1.0


class TestLOF:
    def test_basic(self):
        refs = _ref_matrix(20, 32)
        q = _unit_vec(32, seed=99)
        result = lof_score(q, refs, k=5)
        assert "lof" in result
        assert "ood_score" in result

    def test_in_distribution_query(self):
        refs = _ref_matrix(20, 32, seed=42)
        q = refs[0]  # query IS a reference
        result = lof_score(q, refs, k=5)
        # LOF should be close to 1 for in-distribution
        assert result["lof"] < 2.0

    def test_too_few_refs(self):
        q = _unit_vec(32)
        refs = _ref_matrix(1, 32)
        result = lof_score(q, refs, k=5)
        assert "lof" in result


class TestScoreQuery:
    def test_returns_all_methods(self):
        q = _unit_vec(64)
        refs = _ref_matrix(20, 64)
        result = score_query(q, refs, k=5)
        for method in ["max_similarity", "mean_topk", "similarity_gap",
                       "knn_density", "mahalanobis", "lof"]:
            assert method in result
            assert "ood_score" in result[method]


class TestAUROC:
    def test_perfect_separation(self):
        id_scores = [0.1, 0.2, 0.3]
        ood_scores = [0.7, 0.8, 0.9]
        auroc = compute_auroc(id_scores, ood_scores)
        assert auroc == 1.0

    def test_no_separation(self):
        scores = [0.5, 0.5, 0.5]
        auroc = compute_auroc(scores, scores)
        assert auroc == 0.5

    def test_reversed_separation(self):
        id_scores = [0.7, 0.8, 0.9]
        ood_scores = [0.1, 0.2, 0.3]
        auroc = compute_auroc(id_scores, ood_scores)
        assert auroc == 0.0

    def test_empty(self):
        assert compute_auroc([], [0.5]) == 0.5
        assert compute_auroc([0.5], []) == 0.5


class TestThresholdSweep:
    def test_basic(self):
        id_scores = [0.1, 0.2, 0.3]
        ood_scores = [0.6, 0.7, 0.8]
        results = threshold_sweep(id_scores, ood_scores)
        assert len(results) > 0
        assert all("threshold" in r for r in results)
        assert all("false_ood_rate" in r for r in results)
        assert all("missed_ood_rate" in r for r in results)

    def test_find_best(self):
        id_scores = [0.1, 0.2, 0.3]
        ood_scores = [0.6, 0.7, 0.8]
        sweep = threshold_sweep(id_scores, ood_scores)
        best = find_best_threshold(sweep)
        assert "threshold" in best
        # Best threshold should be between ID and OOD ranges
        assert best["false_ood_rate"] + best["missed_ood_rate"] <= 1.0

    def test_empty(self):
        best = find_best_threshold([])
        assert best["threshold"] == 0.5


class TestSyntheticOODExperiment:
    def test_id_vs_ood_separation(self):
        """Verify OOD methods produce higher scores for OOD than ID."""
        rng = np.random.RandomState(42)

        # In-distribution: cluster around a specific direction
        center = _unit_vec(64, seed=0)
        refs = center + rng.randn(30, 64) * 0.1
        refs = refs / np.linalg.norm(refs, axis=1, keepdims=True)

        # ID query: close to cluster
        id_q = center + rng.randn(64) * 0.1
        id_q = id_q / np.linalg.norm(id_q)

        # OOD query: random direction
        ood_q = _unit_vec(64, seed=99)

        id_scores = score_query(id_q, refs, k=5)
        ood_scores = score_query(ood_q, refs, k=5)

        # OOD should generally have higher ood_score
        assert ood_scores["max_similarity"]["ood_score"] > id_scores["max_similarity"]["ood_score"]
