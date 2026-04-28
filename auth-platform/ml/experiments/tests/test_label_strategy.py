"""Tests for label strategy extraction."""

from experiments.learned_metric_experiment import (
    _extract_sample_group_from_uri,
    _extract_species_from_uri,
    build_label_map,
    extract_label,
)


class TestSpeciesExtraction:
    def test_sheep(self):
        uri = "s3://bucket/external-datasets/raw/Sheep_SBTS25/abc.jpg"
        assert _extract_species_from_uri(uri) == "Sheep"

    def test_buffalo(self):
        uri = "s3://bucket/raw/Buffalo_BBTS12/img.jpg"
        assert _extract_species_from_uri(uri) == "Buffalo"

    def test_cow(self):
        uri = "s3://bucket/raw/Cow_CBTS9/img.jpg"
        assert _extract_species_from_uri(uri) == "Cow"

    def test_goat(self):
        uri = "s3://bucket/raw/Goat_GBTS16/img.jpg"
        assert _extract_species_from_uri(uri) == "Goat"

    def test_lowercase(self):
        uri = "s3://bucket/raw/sheep_SBTS1/img.jpg"
        assert _extract_species_from_uri(uri) == "Sheep"

    def test_no_species(self):
        uri = "s3://bucket/raw/unknown_folder/img.jpg"
        assert _extract_species_from_uri(uri) == "unknown"

    def test_empty_uri(self):
        assert _extract_species_from_uri("") == "unknown"


class TestSampleGroupExtraction:
    def test_basic(self):
        uri = "s3://bucket/raw/Sheep_SBTS25/abc.jpg"
        assert _extract_sample_group_from_uri(uri) == "Sheep_SBTS25"

    def test_deeply_nested(self):
        uri = "s3://bucket/external-datasets/v0.1.0/raw/Cow_CBTS9/img.jpg"
        assert _extract_sample_group_from_uri(uri) == "Cow_CBTS9"


class TestExtractLabel:
    def _make_record(self, species_folder="Sheep_SBTS25"):
        return {
            "reference_image_id": "img-1",
            "reference_item_id": "item-1",
            "region_code": "EXTERNAL_LEATHER_TEXTURE",
            "object_uri": f"s3://bucket/raw/{species_folder}/img.jpg",
            "authenticity_status": "PUBLIC_DATASET_CLASS",
        }

    def test_external_item_id(self):
        assert extract_label(self._make_record(), "external_item_id") == "item-1"

    def test_species(self):
        assert extract_label(self._make_record(), "species") == "Sheep"

    def test_sample_group(self):
        assert extract_label(self._make_record(), "sample_group") == "Sheep_SBTS25"

    def test_region_code(self):
        assert extract_label(self._make_record(), "region_code") == "EXTERNAL_LEATHER_TEXTURE"

    def test_authenticity_status(self):
        assert extract_label(self._make_record(), "authenticity_status") == "PUBLIC_DATASET_CLASS"


class TestBuildLabelMap:
    def test_species_classes(self):
        records = [
            {"object_uri": "s3://b/raw/Sheep_S1/a.jpg", "reference_item_id": "i1"},
            {"object_uri": "s3://b/raw/Sheep_S1/b.jpg", "reference_item_id": "i1"},
            {"object_uri": "s3://b/raw/Cow_C1/c.jpg", "reference_item_id": "i2"},
            {"object_uri": "s3://b/raw/Goat_G1/d.jpg", "reference_item_id": "i3"},
        ]
        labels, mapping = build_label_map(records, "species")
        assert set(mapping.keys()) == {"Cow", "Goat", "Sheep"}
        assert labels == ["Sheep", "Sheep", "Cow", "Goat"]

    def test_single_class_detected(self):
        records = [
            {"object_uri": "s3://b/raw/Sheep_S1/a.jpg", "reference_item_id": "i1"},
            {"object_uri": "s3://b/raw/Sheep_S2/b.jpg", "reference_item_id": "i2"},
        ]
        labels, mapping = build_label_map(records, "species")
        assert len(mapping) == 1  # only Sheep

    def test_external_item_id_many_classes(self):
        records = [{"reference_item_id": f"item-{i}", "object_uri": ""} for i in range(10)]
        labels, mapping = build_label_map(records, "external_item_id")
        assert len(mapping) == 10
