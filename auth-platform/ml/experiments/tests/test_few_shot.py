"""Unit tests for few_shot.py — synthetic numpy only, no DB / no datasets."""

from __future__ import annotations

import random

import numpy as np
import pytest

from experiments import few_shot


def _unit(*components: float) -> np.ndarray:
    arr = np.asarray(components, dtype=np.float64)
    n = float(np.linalg.norm(arr))
    return arr / n if n > 0 else arr


def _make_records(per_class: int = 6, classes: tuple[str, ...] = ("a", "b", "c")) -> list[dict]:
    """Three well-separated classes near the +x, +y, +z axes."""
    rng = np.random.default_rng(0)
    records: list[dict] = []
    centers = {"a": (1.0, 0.0, 0.0), "b": (0.0, 1.0, 0.0), "c": (0.0, 0.0, 1.0)}
    for cls in classes:
        cx, cy, cz = centers[cls]
        for i in range(per_class):
            jitter = rng.normal(0, 0.05, size=3)
            v = _unit(cx + jitter[0], cy + jitter[1], cz + jitter[2])
            records.append(
                {
                    "embedding": v,
                    "label": cls,
                    "split": "train" if i < per_class // 2 else "test",
                }
            )
    return records


# ---------------------------------------------------------------------------
# group_embeddings_by_label
# ---------------------------------------------------------------------------


def test_group_embeddings_by_label_no_filter():
    records = _make_records(per_class=4)
    grouped = few_shot.group_embeddings_by_label(records, label_strategy="label")
    assert set(grouped) == {"a", "b", "c"}
    assert all(len(v) == 4 for v in grouped.values())


def test_group_embeddings_by_label_split_filter_actually_filters():
    """The headline contract: split_filter must drop records before grouping."""
    records = _make_records(per_class=6)
    train_only = few_shot.group_embeddings_by_label(
        records, label_strategy="label", split_filter={"train"}
    )
    test_only = few_shot.group_embeddings_by_label(
        records, label_strategy="label", split_filter={"test"}
    )
    for cls in ("a", "b", "c"):
        assert len(train_only[cls]) == 3
        assert len(test_only[cls]) == 3
    combined_count = sum(len(v) for v in train_only.values()) + sum(len(v) for v in test_only.values())
    assert combined_count == len(records)


def test_group_embeddings_by_label_empty_split_filter_raises():
    records = _make_records()
    with pytest.raises(ValueError, match="zero records"):
        few_shot.group_embeddings_by_label(records, label_strategy="label", split_filter={"holdout"})


def test_group_embeddings_by_label_too_few_classes_raises():
    records = _make_records(per_class=4, classes=("a",))
    with pytest.raises(ValueError, match="need at least 2"):
        few_shot.group_embeddings_by_label(records, label_strategy="label")


def test_group_embeddings_by_label_missing_key_raises():
    records = [{"embedding": _unit(1, 0, 0), "split": "train"}]
    with pytest.raises(KeyError):
        few_shot.group_embeddings_by_label(records, label_strategy="label")


# ---------------------------------------------------------------------------
# sample_episode
# ---------------------------------------------------------------------------


def test_sample_episode_no_overlap_between_support_and_query():
    grouped = few_shot.group_embeddings_by_label(_make_records(per_class=8), label_strategy="label")
    rng = random.Random(42)
    out = few_shot.sample_episode(grouped, ways=None, shots=3, query_per_class=2, rng=rng)
    assert out is not None
    support, query = out
    for cls in support:
        s_set = {e.tobytes() for e in support[cls]}
        q_set = {e.tobytes() for e in query[cls]}
        assert s_set.isdisjoint(q_set), f"support/query overlap detected in class {cls}"
        assert len(support[cls]) == 3
        assert len(query[cls]) == 2


def test_sample_episode_deterministic_with_seed():
    grouped = few_shot.group_embeddings_by_label(_make_records(per_class=8), label_strategy="label")
    a = few_shot.sample_episode(grouped, None, 3, 2, random.Random(7))
    b = few_shot.sample_episode(grouped, None, 3, 2, random.Random(7))
    assert a is not None and b is not None
    for cls in a[0]:
        for x, y in zip(a[0][cls], b[0][cls], strict=True):
            assert np.allclose(x, y)


def test_sample_episode_returns_none_when_classes_lack_capacity():
    grouped = {"x": [_unit(1, 0, 0)], "y": [_unit(0, 1, 0)]}  # 1 each
    out = few_shot.sample_episode(grouped, None, shots=2, query_per_class=1, rng=random.Random(0))
    assert out is None


def test_sample_episode_ways_caps_class_count():
    grouped = few_shot.group_embeddings_by_label(_make_records(per_class=8), label_strategy="label")
    out = few_shot.sample_episode(grouped, ways=2, shots=2, query_per_class=1, rng=random.Random(0))
    assert out is not None
    support, query = out
    assert len(support) == 2
    assert len(query) == 2


# ---------------------------------------------------------------------------
# Prototype math
# ---------------------------------------------------------------------------


def test_prototype_centroid_l2_normalized():
    embs = [_unit(1, 0, 0), _unit(0.95, 0.1, 0), _unit(0.9, 0.0, 0.1)]
    proto = few_shot.prototype_centroid(embs)
    assert np.isclose(np.linalg.norm(proto), 1.0, atol=1e-6)
    assert proto[0] > 0.9


def test_prototype_medoid_single_returns_itself():
    e = _unit(0.3, 0.7, 0.6)
    out = few_shot.prototype_medoid([e])
    assert np.allclose(out, e)


def test_prototype_medoid_picks_central():
    central = _unit(1, 0, 0)
    neighbors = [central, _unit(0.99, 0.01, 0), _unit(0.99, -0.01, 0), _unit(0.5, 0.5, 0)]
    out = few_shot.prototype_medoid(neighbors)
    assert np.allclose(out, central) or np.allclose(out, neighbors[1]) or np.allclose(out, neighbors[2])
    assert not np.allclose(out, neighbors[3])


# ---------------------------------------------------------------------------
# Inference strategies
# ---------------------------------------------------------------------------


def _build_support_query():
    grouped = few_shot.group_embeddings_by_label(_make_records(per_class=8), label_strategy="label")
    out = few_shot.sample_episode(grouped, None, 3, 3, random.Random(0))
    assert out is not None
    return out


def test_nearest_neighbor_classifies_well_on_separated_classes():
    support, query = _build_support_query()
    correct = 0
    total = 0
    for true_c, qs in query.items():
        for q in qs:
            r = few_shot.nearest_neighbor_strategy(q, support)
            assert r.top1_score >= r.top2_score
            if r.predicted_class == true_c:
                correct += 1
            total += 1
    assert correct / total > 0.9


def test_top_k_mean_classifies_well():
    support, query = _build_support_query()
    correct = 0
    for true_c, qs in query.items():
        for q in qs:
            r = few_shot.top_k_mean_strategy(q, support, k=3)
            if r.predicted_class == true_c:
                correct += 1
    assert correct >= len(query) * 2  # most queries correct (3 classes * 3 queries)


def test_prototype_centroid_classifies_well():
    support, query = _build_support_query()
    correct = sum(
        1
        for true_c, qs in query.items()
        for q in qs
        if few_shot.prototype_centroid_strategy(q, support).predicted_class == true_c
    )
    assert correct >= 7  # 9 queries on well-separated classes


def test_prototype_medoid_classifies_well():
    support, query = _build_support_query()
    correct = sum(
        1
        for true_c, qs in query.items()
        for q in qs
        if few_shot.prototype_medoid_strategy(q, support).predicted_class == true_c
    )
    assert correct >= 7


# ---------------------------------------------------------------------------
# Abstention curve
# ---------------------------------------------------------------------------


def test_abstention_curve_monotonic_in_score_threshold():
    """Higher score thresholds must give >= abstention rate."""
    qr = [
        ("a", "a", 0.95, 0.30),
        ("a", "a", 0.85, 0.40),
        ("b", "b", 0.75, 0.20),
        ("c", "a", 0.55, 0.10),
        ("c", "c", 0.45, 0.10),
    ]
    curve = few_shot.evaluate_with_abstention_curve(
        qr,
        score_thresholds=[0.0, 0.5, 0.7, 0.9],
        margin_thresholds=[0.0],
    )
    by_score = {r["score_threshold"]: r["abstention_rate"] for r in curve}
    assert by_score[0.0] <= by_score[0.5] <= by_score[0.7] <= by_score[0.9]


def test_abstention_curve_monotonic_in_margin_threshold():
    qr = [
        ("a", "a", 0.95, 0.30),
        ("a", "a", 0.85, 0.80),
        ("b", "b", 0.75, 0.50),
        ("c", "c", 0.65, 0.10),
    ]
    curve = few_shot.evaluate_with_abstention_curve(
        qr,
        score_thresholds=[0.0],
        margin_thresholds=[0.0, 0.05, 0.2, 0.5],
    )
    by_margin = {r["margin_threshold"]: r["abstention_rate"] for r in curve}
    assert by_margin[0.0] <= by_margin[0.05] <= by_margin[0.2] <= by_margin[0.5]


def test_abstention_curve_is_flat_list_of_records():
    qr = [("a", "a", 0.9, 0.1)]
    curve = few_shot.evaluate_with_abstention_curve(qr, [0.0, 0.5], [0.0, 0.05, 0.1])
    assert isinstance(curve, list)
    assert len(curve) == 6
    assert all(isinstance(r, dict) for r in curve)
    expected_keys = {"score_threshold", "margin_threshold", "abstention_rate", "coverage", "accuracy_after_abstention"}
    assert expected_keys.issubset(curve[0].keys())


def test_abstention_curve_zero_thresholds_keeps_everything():
    qr = [("a", "a", 0.9, 0.1), ("b", "a", 0.5, 0.4), ("c", "c", 0.7, 0.2)]
    curve = few_shot.evaluate_with_abstention_curve(qr, [0.0], [0.0])
    assert curve[0]["abstention_rate"] == 0.0
    assert curve[0]["total_after_abstention"] == 3
    assert curve[0]["correct_after_abstention"] == 2
    assert curve[0]["accuracy_after_abstention"] == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# Variance + run_episode
# ---------------------------------------------------------------------------


def test_support_set_variance_returns_expected_stats():
    accs = [0.6, 0.7, 0.8, 0.9, 1.0]
    stats = few_shot.support_set_variance(accs)
    assert stats["n"] == 5
    assert stats["mean"] == pytest.approx(0.8)
    assert 0 <= stats["std"] <= 1
    assert stats["p05"] <= stats["mean"] <= stats["p95"]


def test_support_set_variance_empty_input_safe():
    stats = few_shot.support_set_variance([])
    assert stats["n"] == 0
    assert stats["mean"] == 0.0


def test_run_episode_records_match_query_count():
    support, query = _build_support_query()
    acc, records = few_shot.run_episode(support, query, "prototype_centroid")
    expected_total = sum(len(v) for v in query.values())
    assert len(records) == expected_total
    assert 0.0 <= acc <= 1.0


def test_run_episode_unknown_strategy_raises():
    support, query = _build_support_query()
    with pytest.raises(ValueError, match="unknown strategy"):
        few_shot.run_episode(support, query, "not_a_real_strategy")
