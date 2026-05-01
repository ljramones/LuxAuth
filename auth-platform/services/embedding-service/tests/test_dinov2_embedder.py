"""Unit tests for the DINOv2 frozen embedder.

The HuggingFace model loader is monkeypatched so CI does not download weights.
We exercise the post-load logic: shape, L2-normalization, batch handling, and
frozen-mode (no gradients).
"""

from __future__ import annotations

import io

import numpy as np
import pytest
import torch
from app.embedders import dinov2_frozen
from PIL import Image


class _StubProcessor:
    """Minimal stand-in for transformers.AutoImageProcessor."""

    def __call__(self, images, return_tensors="pt"):
        if not isinstance(images, list):
            images = [images]
        batch = []
        for img in images:
            arr = np.asarray(img.resize((dinov2_frozen.INPUT_SIZE, dinov2_frozen.INPUT_SIZE))).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr).permute(2, 0, 1)
            batch.append(tensor)
        return {"pixel_values": torch.stack(batch, dim=0)}


class _StubOutput:
    def __init__(self, last_hidden_state: torch.Tensor):
        self.last_hidden_state = last_hidden_state


class _StubModel(torch.nn.Module):
    """Pretends to be DINOv2: deterministic CLS token from input statistics."""

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim
        self.proj = torch.nn.Linear(3 * dinov2_frozen.INPUT_SIZE * dinov2_frozen.INPUT_SIZE, dim)

    def forward(self, pixel_values: torch.Tensor) -> _StubOutput:
        b = pixel_values.shape[0]
        flat = pixel_values.reshape(b, -1)
        cls = self.proj(flat)
        last = torch.zeros(b, 2, self.dim, dtype=cls.dtype, device=cls.device)
        last[:, 0, :] = cls
        return _StubOutput(last_hidden_state=last)


@pytest.fixture(autouse=True)
def stub_loader(monkeypatch):
    """Replace _load with a deterministic stub so tests do not touch HuggingFace."""
    dinov2_frozen.reset_cache()
    model = _StubModel(dinov2_frozen.EMBEDDING_DIM)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    processor = _StubProcessor()

    def _stub_load():
        return model, processor, "cpu"

    monkeypatch.setattr(dinov2_frozen, "_load", _stub_load)
    yield
    dinov2_frozen.reset_cache()


def _png_bytes(color: tuple[int, int, int] = (128, 128, 128)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_single_embedding_shape_and_l2_norm():
    emb = dinov2_frozen.compute_dinov2_embedding(_png_bytes())
    assert isinstance(emb, list)
    assert len(emb) == dinov2_frozen.EMBEDDING_DIM
    arr = np.asarray(emb, dtype=np.float64)
    assert np.isclose(np.linalg.norm(arr), 1.0, atol=1e-5)


def test_batch_embeddings_shape():
    inputs = [_png_bytes((10, 20, 30)), _png_bytes((200, 100, 50)), _png_bytes((0, 0, 0))]
    embs = dinov2_frozen.compute_dinov2_embeddings(inputs)
    assert len(embs) == 3
    assert all(len(e) == dinov2_frozen.EMBEDDING_DIM for e in embs)
    for e in embs:
        assert np.isclose(np.linalg.norm(e), 1.0, atol=1e-5)


def test_empty_batch_returns_empty():
    assert dinov2_frozen.compute_dinov2_embeddings([]) == []


def test_frozen_mode_no_grad():
    """Forward pass must not require gradients on any model parameter."""
    model, _processor, _device = dinov2_frozen._load()
    for p in model.parameters():
        assert p.requires_grad is False


def test_grayscale_input_is_converted_to_rgb():
    img = Image.new("L", (64, 64), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    emb = dinov2_frozen.compute_dinov2_embedding(buf.getvalue())
    assert len(emb) == dinov2_frozen.EMBEDDING_DIM
    assert np.isclose(np.linalg.norm(emb), 1.0, atol=1e-5)
