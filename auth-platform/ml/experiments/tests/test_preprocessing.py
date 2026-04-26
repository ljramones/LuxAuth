"""Tests for preprocessing strategies."""

import io

import numpy as np
import pytest
from PIL import Image

from experiments.preprocessing import (
    ALL_STRATEGY_NAMES,
    STRATEGIES,
    center_crop_512,
    clahe_center_crop_512,
    five_crop_512,
    grayscale_center_crop_512,
    padded_resize_512,
    tile_224_average,
)
from experiments.preprocessing_experiment import aggregate_embeddings, run_strategy


def _make_test_image(width: int = 640, height: int = 480, seed: int = 42) -> bytes:
    """Create a deterministic test image."""
    rng = np.random.RandomState(seed)
    arr = rng.randint(0, 255, (height, width, 3), dtype=np.uint8)
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _image_size(data: bytes) -> tuple[int, int]:
    img = Image.open(io.BytesIO(data))
    return img.size


class TestCenterCrop512:
    def test_output_size(self):
        result = center_crop_512(_make_test_image())
        assert len(result) == 1
        assert _image_size(result[0]) == (512, 512)

    def test_square_input(self):
        result = center_crop_512(_make_test_image(500, 500))
        assert _image_size(result[0]) == (512, 512)

    def test_deterministic(self):
        img = _make_test_image()
        r1 = center_crop_512(img)
        r2 = center_crop_512(img)
        assert r1[0] == r2[0]


class TestPaddedResize512:
    def test_output_size(self):
        result = padded_resize_512(_make_test_image())
        assert len(result) == 1
        assert _image_size(result[0]) == (512, 512)

    def test_wide_image(self):
        result = padded_resize_512(_make_test_image(1000, 200))
        assert _image_size(result[0]) == (512, 512)

    def test_tall_image(self):
        result = padded_resize_512(_make_test_image(200, 1000))
        assert _image_size(result[0]) == (512, 512)

    def test_deterministic(self):
        img = _make_test_image()
        r1 = padded_resize_512(img)
        r2 = padded_resize_512(img)
        assert r1[0] == r2[0]


class TestFiveCrop512:
    def test_returns_five_images(self):
        result = five_crop_512(_make_test_image())
        assert len(result) == 5

    def test_each_crop_size(self):
        result = five_crop_512(_make_test_image())
        for crop in result:
            assert _image_size(crop) == (512, 512)

    def test_square_input(self):
        result = five_crop_512(_make_test_image(512, 512))
        assert len(result) == 5


class TestGrayscaleCenterCrop512:
    def test_output_size(self):
        result = grayscale_center_crop_512(_make_test_image())
        assert len(result) == 1
        assert _image_size(result[0]) == (512, 512)

    def test_output_is_rgb(self):
        result = grayscale_center_crop_512(_make_test_image())
        img = Image.open(io.BytesIO(result[0]))
        assert img.mode == "RGB"

    def test_grayscale_channels_equal(self):
        result = grayscale_center_crop_512(_make_test_image())
        arr = np.array(Image.open(io.BytesIO(result[0])))
        # All three channels should be identical (grayscale converted to RGB)
        assert np.array_equal(arr[:, :, 0], arr[:, :, 1])
        assert np.array_equal(arr[:, :, 1], arr[:, :, 2])


class TestClaheCenterCrop512:
    def test_output_size(self):
        result = clahe_center_crop_512(_make_test_image())
        assert len(result) == 1
        assert _image_size(result[0]) == (512, 512)

    def test_deterministic(self):
        img = _make_test_image()
        r1 = clahe_center_crop_512(img)
        r2 = clahe_center_crop_512(img)
        assert r1[0] == r2[0]


class TestTile224Average:
    def test_produces_at_least_one_tile(self):
        result = tile_224_average(_make_test_image())
        assert len(result) >= 1

    def test_tile_size(self):
        result = tile_224_average(_make_test_image())
        for tile in result:
            assert _image_size(tile) == (224, 224)

    def test_small_image(self):
        result = tile_224_average(_make_test_image(100, 100))
        assert len(result) >= 1
        assert _image_size(result[0]) == (224, 224)

    def test_large_image_multiple_tiles(self):
        result = tile_224_average(_make_test_image(800, 600))
        assert len(result) > 1


class TestAggregation:
    def test_single_embedding_passthrough(self):
        emb = [1.0, 0.0, 0.0]
        result = aggregate_embeddings([emb])
        assert result == emb

    def test_average_and_normalize(self):
        emb1 = [1.0, 0.0]
        emb2 = [0.0, 1.0]
        result = aggregate_embeddings([emb1, emb2])
        norm = np.linalg.norm(result)
        assert 0.99 < norm < 1.01

    def test_empty_returns_empty(self):
        assert aggregate_embeddings([]) == []


class TestStrategyRegistry:
    def test_all_strategies_registered(self):
        assert len(STRATEGIES) == 6
        assert set(STRATEGIES.keys()) == set(ALL_STRATEGY_NAMES)

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            run_strategy("nonexistent_strategy", [], [], [])


class TestSyntheticDatasetMetrics:
    def test_metrics_with_tiny_dataset(self):
        """Verify metrics computation works with synthetic preprocessing output."""
        # Create synthetic images with different seeds for different "classes"
        imgs = [_make_test_image(seed=i) for i in range(10)]
        labels = ["A"] * 5 + ["B"] * 5
        regions = ["R1"] * 10

        result = run_strategy("center_crop_512", imgs, labels, regions, "texture_baseline_v0.2.0")
        m = result["metrics"]
        assert m["count"] == 10
        assert m["dimension"] > 0
        assert "cluster_separation" in m
        assert "nn_agreement_rate" in m
        assert "recall_at_1" in m
