"""Tests for experiment metrics."""


from experiments.metrics import compute_metrics


def test_basic_metrics():
    embeddings = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]]
    labels = ["A", "A", "B", "B"]
    m = compute_metrics(embeddings, labels)
    assert m["count"] == 4
    assert m["dimension"] == 2
    assert m["nn_agreement"] >= 0


def test_single_class():
    embeddings = [[1.0, 0.0], [0.9, 0.1], [0.8, 0.2]]
    labels = ["A", "A", "A"]
    m = compute_metrics(embeddings, labels)
    assert m["count"] == 3
    assert m["nn_agreement_rate"] == 1.0
    assert m["diff_label_mean"] == 0.0


def test_empty():
    m = compute_metrics([], [])
    assert m["count"] == 0


def test_recall_at_k():
    embeddings = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]]
    labels = ["A", "A", "B", "B"]
    m = compute_metrics(embeddings, labels)
    assert 0.0 <= m["recall_at_1"] <= 1.0
    assert m["recall_at_1"] <= m["recall_at_3"] <= m["recall_at_5"]
