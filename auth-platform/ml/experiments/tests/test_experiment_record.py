"""Tests for experiment record creation."""

from experiments.experiment_record import create_record


def test_record_has_required_fields():
    rec = create_record(
        dataset_version="test_v0.1.0",
        feature_extractor="test_extractor",
        embedding_dimension=128,
        metrics={"count": 10},
    )
    assert "experiment_id" in rec
    assert "timestamp" in rec
    assert rec["dataset_version"] == "test_v0.1.0"
    assert rec["feature_extractor"] == "test_extractor"
    assert rec["embedding_dimension"] == 128
    assert rec["metrics"]["count"] == 10
