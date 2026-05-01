"""Unit tests for embedder dispatch in app.handlers._select_embedder.

The dispatch table is the contract between embedding_model_version strings
and the embedder backends. These tests pin that mapping and document the
fallback behavior for unknown / future model versions.
"""

from app.handlers import (
    _embed_dinov2_frozen,
    _embed_learned_metric,
    _embed_texture_baseline,
    _embed_texture_baseline_v2,
    _select_embedder,
)


def test_dispatch_dinov2():
    assert _select_embedder("dinov2_base_frozen_v0.1.0") is _embed_dinov2_frozen


def test_dispatch_learned_metric():
    assert _select_embedder("learned_metric_v0.1.0") is _embed_learned_metric
    assert _select_embedder("learned_metric_v0.2.0") is _embed_learned_metric


def test_dispatch_texture_baseline_v2():
    assert _select_embedder("texture_baseline_v0.2.0") is _embed_texture_baseline_v2


def test_dispatch_texture_baseline_v1():
    assert _select_embedder("texture_baseline_v0.1.0") is _embed_texture_baseline


def test_dispatch_unknown_model_falls_back_to_baseline():
    """Unknown model versions fall through to the texture_baseline default.

    This is the safe-by-default behavior for the live pipeline. If we want
    strict rejection of unknown versions in the future, switch this to raise
    and update both the dispatch and the regression test together.
    """
    assert _select_embedder("nonexistent_model_v0.0.0") is _embed_texture_baseline
    assert _select_embedder("") is _embed_texture_baseline
