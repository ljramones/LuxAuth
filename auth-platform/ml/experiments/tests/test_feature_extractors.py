"""Tests for feature extractors — use synthetic images, no real datasets required."""

import io
import math

import numpy as np
from PIL import Image

from experiments.feature_extractors import texture_baseline_v010, texture_baseline_v020


def _make_test_image(seed: int = 42) -> bytes:
    rng = np.random.RandomState(seed)
    arr = rng.randint(50, 200, (256, 256, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def test_v010_dimension():
    img = _make_test_image()
    emb = texture_baseline_v010(img)
    assert len(emb) == 128


def test_v010_deterministic():
    img = _make_test_image(seed=99)
    emb1 = texture_baseline_v010(img)
    emb2 = texture_baseline_v010(img)
    assert emb1 == emb2


def test_v010_unit_norm():
    img = _make_test_image()
    emb = texture_baseline_v010(img)
    norm = math.sqrt(sum(x * x for x in emb))
    assert 0.95 <= norm <= 1.05


def test_v020_dimension():
    img = _make_test_image()
    emb = texture_baseline_v020(img)
    assert len(emb) == 256


def test_v020_deterministic():
    img = _make_test_image(seed=77)
    emb1 = texture_baseline_v020(img)
    emb2 = texture_baseline_v020(img)
    assert emb1 == emb2


def test_v020_unit_norm():
    img = _make_test_image()
    emb = texture_baseline_v020(img)
    norm = math.sqrt(sum(x * x for x in emb))
    assert 0.95 <= norm <= 1.05


def test_v020_different_from_v010():
    img = _make_test_image()
    emb1 = texture_baseline_v010(img)
    emb2 = texture_baseline_v020(img)
    assert len(emb1) != len(emb2)  # different dimensions
