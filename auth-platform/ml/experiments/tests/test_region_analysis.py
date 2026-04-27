"""Tests for region analysis utilities."""


import numpy as np

from experiments.region_analysis import (
    READINESS_THRESHOLDS,
    REGION_METADATA,
    compute_per_region_metrics,
    compute_readiness,
    compute_region_coverage,
    format_coverage_table,
    format_metrics_table,
    get_region_meta,
    is_external_region,
)


def _make_records(region_code: str, n: int, item_prefix: str = "item",
                  split: str = "train", label: str = "AUTHENTIC") -> list[dict]:
    """Create synthetic dataset records for testing."""
    return [
        {
            "reference_image_id": f"img-{region_code}-{i}",
            "reference_item_id": f"{item_prefix}-{i}",
            "region_code": region_code,
            "split": split,
            "authenticity_status": label,
        }
        for i in range(n)
    ]


def _make_embedding(dim: int = 256, seed: int = 0) -> list[float]:
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


class TestReadiness:
    def test_no_data(self):
        assert compute_readiness(0) == "no_data"

    def test_sparse(self):
        assert compute_readiness(1) == "sparse"
        assert compute_readiness(9) == "sparse"

    def test_diagnostic_only(self):
        assert compute_readiness(10) == "diagnostic_only"
        assert compute_readiness(24) == "diagnostic_only"

    def test_evaluation_ready(self):
        assert compute_readiness(25) == "evaluation_ready"
        assert compute_readiness(99) == "evaluation_ready"

    def test_training_candidate(self):
        assert compute_readiness(100) == "training_candidate"
        assert compute_readiness(1000) == "training_candidate"

    def test_thresholds_consistent(self):
        assert READINESS_THRESHOLDS["no_data"] == 0
        assert READINESS_THRESHOLDS["sparse"] < READINESS_THRESHOLDS["diagnostic_only"]
        assert READINESS_THRESHOLDS["diagnostic_only"] < READINESS_THRESHOLDS["evaluation_ready"]
        assert READINESS_THRESHOLDS["evaluation_ready"] < READINESS_THRESHOLDS["training_candidate"]


class TestRegionMetadata:
    def test_known_region(self):
        meta = get_region_meta("EXTERIOR_CANVAS")
        assert meta["known"] is True
        assert meta["tier"] == 1

    def test_external_region(self):
        meta = get_region_meta("EXTERNAL_FABRIC_TEXTURE")
        assert meta["known"] is True
        assert meta["external_dataset_only"] is True

    def test_unknown_region(self):
        meta = get_region_meta("TOTALLY_UNKNOWN_REGION")
        assert meta["known"] is False
        assert meta["inspection_layer"] == "unknown"

    def test_is_external(self):
        assert is_external_region("EXTERNAL_FABRIC_TEXTURE") is True
        assert is_external_region("EXTERNAL_LEATHER_TEXTURE") is True
        assert is_external_region("EXTERIOR_CANVAS") is False
        assert is_external_region("HARDWARE_ENGRAVING") is False

    def test_all_known_regions_have_required_fields(self):
        for rc, meta in REGION_METADATA.items():
            assert "inspection_layer" in meta, f"{rc} missing inspection_layer"
            assert "tier" in meta, f"{rc} missing tier"
            assert "external_dataset_only" in meta, f"{rc} missing external_dataset_only"


class TestRegionCoverage:
    def test_single_region(self):
        records = _make_records("EXTERIOR_CANVAS", 20)
        coverage = compute_region_coverage(records)
        assert len(coverage) == 1
        assert coverage[0]["region_code"] == "EXTERIOR_CANVAS"
        assert coverage[0]["image_count"] == 20
        assert coverage[0]["readiness"] == "diagnostic_only"

    def test_multiple_regions(self):
        records = (
            _make_records("EXTERIOR_CANVAS", 50) +
            _make_records("HARDWARE_ENGRAVING", 5)
        )
        coverage = compute_region_coverage(records)
        assert len(coverage) == 2
        by_rc = {c["region_code"]: c for c in coverage}
        assert by_rc["EXTERIOR_CANVAS"]["readiness"] == "evaluation_ready"
        assert by_rc["HARDWARE_ENGRAVING"]["readiness"] == "sparse"

    def test_sparse_warning(self):
        records = _make_records("STITCHING_DETAIL", 3)
        coverage = compute_region_coverage(records)
        assert "sparse_coverage" in coverage[0]["warnings"]

    def test_external_warning(self):
        records = _make_records("EXTERNAL_FABRIC_TEXTURE", 100)
        coverage = compute_region_coverage(records)
        assert "external_dataset_only" in coverage[0]["warnings"]

    def test_unknown_region_warning(self):
        records = _make_records("MADE_UP_REGION", 10)
        coverage = compute_region_coverage(records)
        assert "unknown_region_code" in coverage[0]["warnings"]

    def test_splits_counted(self):
        records = (
            _make_records("EXTERIOR_CANVAS", 10, split="train") +
            _make_records("EXTERIOR_CANVAS", 5, split="test")
        )
        coverage = compute_region_coverage(records)
        assert coverage[0]["splits"] == {"test": 5, "train": 10}

    def test_labels_counted(self):
        records = (
            _make_records("EXTERIOR_CANVAS", 7, label="AUTHENTIC") +
            _make_records("EXTERIOR_CANVAS", 3, label="COUNTERFEIT", item_prefix="bad")
        )
        coverage = compute_region_coverage(records)
        assert coverage[0]["labels"] == {"AUTHENTIC": 7, "COUNTERFEIT": 3}

    def test_item_count_deduplication(self):
        records = _make_records("EXTERIOR_CANVAS", 5, item_prefix="same-item")
        # Give them all the same item ID
        for r in records:
            r["reference_item_id"] = "same-item-0"
        coverage = compute_region_coverage(records)
        assert coverage[0]["item_count"] == 1


class TestPerRegionMetrics:
    def test_with_embeddings(self):
        records = _make_records("EXTERIOR_CANVAS", 10, label="A") + \
                  _make_records("EXTERIOR_CANVAS", 10, label="B", item_prefix="b")
        embeddings = {}
        for i, r in enumerate(records):
            embeddings[r["reference_image_id"]] = _make_embedding(seed=i)

        results = compute_per_region_metrics(records, embeddings, min_images=2)
        assert len(results) == 1
        assert results[0]["region_code"] == "EXTERIOR_CANVAS"
        assert results[0]["metrics"] is not None
        assert "cluster_separation" in results[0]["metrics"]

    def test_skipped_when_too_few(self):
        records = _make_records("HARDWARE_ENGRAVING", 1)
        embeddings = {records[0]["reference_image_id"]: _make_embedding()}

        results = compute_per_region_metrics(records, embeddings, min_images=5)
        assert len(results) == 1
        assert results[0]["metrics"] is None
        assert "fewer than" in results[0]["note"]

    def test_single_label_note(self):
        records = _make_records("EXTERNAL_FABRIC_TEXTURE", 20, label="PUBLIC_DATASET_CLASS")
        embeddings = {}
        for i, r in enumerate(records):
            embeddings[r["reference_image_id"]] = _make_embedding(seed=i)

        results = compute_per_region_metrics(records, embeddings, min_images=2)
        assert "single-label" in results[0]["note"]

    def test_missing_embeddings_excluded(self):
        records = _make_records("EXTERIOR_CANVAS", 10)
        # Only give embeddings for first 5
        embeddings = {}
        for i in range(5):
            embeddings[records[i]["reference_image_id"]] = _make_embedding(seed=i)

        results = compute_per_region_metrics(records, embeddings, min_images=2)
        assert results[0]["embedding_count"] == 5


class TestFormatting:
    def test_coverage_table_has_headers(self):
        records = _make_records("EXTERIOR_CANVAS", 20)
        coverage = compute_region_coverage(records)
        table = format_coverage_table(coverage)
        assert "Region" in table
        assert "EXTERIOR_CANVAS" in table

    def test_metrics_table_handles_none(self):
        region_metrics = [{
            "region_code": "SPARSE_REGION",
            "embedding_count": 1,
            "metrics": None,
            "note": "too few",
        }]
        table = format_metrics_table(region_metrics)
        assert "SPARSE_REGION" in table
        assert "too few" in table

    def test_metrics_table_with_data(self):
        records = _make_records("EXTERIOR_CANVAS", 10)
        embeddings = {r["reference_image_id"]: _make_embedding(seed=i) for i, r in enumerate(records)}
        region_metrics = compute_per_region_metrics(records, embeddings, min_images=2)
        table = format_metrics_table(region_metrics)
        assert "EXTERIOR_CANVAS" in table


class TestSyntheticAnalysis:
    def test_full_analysis_pipeline(self):
        """Verify the full analysis pipeline works on synthetic data."""
        records = (
            _make_records("EXTERIOR_CANVAS", 30, label="AUTHENTIC") +
            _make_records("EXTERIOR_CANVAS", 20, label="COUNTERFEIT", item_prefix="c") +
            _make_records("HARDWARE_ENGRAVING", 5, label="AUTHENTIC") +
            _make_records("EXTERNAL_FABRIC_TEXTURE", 100, label="PUBLIC_DATASET_CLASS")
        )

        coverage = compute_region_coverage(records)
        assert len(coverage) == 3

        by_rc = {c["region_code"]: c for c in coverage}
        assert by_rc["EXTERIOR_CANVAS"]["readiness"] == "evaluation_ready"
        assert by_rc["HARDWARE_ENGRAVING"]["readiness"] == "sparse"
        assert by_rc["EXTERNAL_FABRIC_TEXTURE"]["readiness"] == "training_candidate"

        embeddings = {}
        for i, r in enumerate(records):
            embeddings[r["reference_image_id"]] = _make_embedding(seed=i)

        region_metrics = compute_per_region_metrics(records, embeddings, min_images=10)
        met_map = {rm["region_code"]: rm for rm in region_metrics}

        assert met_map["EXTERIOR_CANVAS"]["metrics"] is not None
        assert met_map["HARDWARE_ENGRAVING"]["metrics"] is None  # too few
        assert met_map["EXTERNAL_FABRIC_TEXTURE"]["metrics"] is not None
        assert "single-label" in met_map["EXTERNAL_FABRIC_TEXTURE"]["note"]
