"""DINOv2 ViT-B/14 frozen-backbone embedder.

CLS token from the final transformer layer, L2-normalized to a 768-d vector.
Weights are frozen; no gradients are computed. The model is loaded lazily on
first use and cached at module scope so subsequent calls reuse it.
"""

from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    import torch as torch_t

EMBEDDING_DIM = 768
HF_MODEL_ID = "facebook/dinov2-base"
HF_REVISION = "f9e44c814b77203eaa57a6bdbbd535f21ede1415"
INPUT_SIZE = 224

_model = None
_processor = None
_device: str | None = None


def _select_device() -> str:
    override = os.environ.get("DINOV2_DEVICE")
    if override:
        return override
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load() -> tuple[torch_t.nn.Module, object, str]:
    global _model, _processor, _device
    if _model is not None and _processor is not None and _device is not None:
        return _model, _processor, _device

    from transformers import AutoImageProcessor, AutoModel

    device = _select_device()
    processor = AutoImageProcessor.from_pretrained(HF_MODEL_ID, revision=HF_REVISION)
    model = AutoModel.from_pretrained(HF_MODEL_ID, revision=HF_REVISION)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)

    _model = model
    _processor = processor
    _device = device
    return model, processor, device


def _to_pil(norm_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(norm_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def compute_dinov2_embedding(norm_bytes: bytes) -> list[float]:
    """Single-image convenience wrapper around :func:`compute_dinov2_embeddings`."""
    return compute_dinov2_embeddings([norm_bytes])[0]


def compute_dinov2_embeddings(norm_bytes_batch: list[bytes]) -> list[list[float]]:
    """Embed a batch of normalized image bytes.

    Returns a list of L2-normalized 768-d embeddings, one per input. Inputs
    are resized via the HF image processor (bilinear to the model's expected
    size). The forward pass runs under ``torch.no_grad`` on a frozen model.
    """
    if not norm_bytes_batch:
        return []

    import torch

    model, processor, device = _load()
    images = [_to_pil(b) for b in norm_bytes_batch]
    inputs = processor(images=images, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)

    with torch.no_grad():
        outputs = model(pixel_values=pixel_values)
    cls = outputs.last_hidden_state[:, 0, :]
    cls = torch.nn.functional.normalize(cls, p=2, dim=1)
    return cls.detach().cpu().numpy().astype(np.float32).tolist()


def reset_cache() -> None:
    """Clear the module-scope model cache. Intended for tests."""
    global _model, _processor, _device
    _model = None
    _processor = None
    _device = None
