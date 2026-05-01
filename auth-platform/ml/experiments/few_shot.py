"""Few-shot prototype-matching utilities for Phase 10.

Operates on pre-labeled, embedding-bearing records. Each record is a dict
with at least these keys:

  - ``embedding``    : numpy array, L2-normalized
  - ``split``        : str, e.g. "train" / "validation" / "test"
  - <label_strategy> : str, the label under the chosen strategy
                       (e.g. ``record["species"]`` when label_strategy="species")

The DB-loading and label-attachment logic lives in
``scripts/run_few_shot_experiment.py``; this module is intentionally pure so
it can be unit-tested with synthetic numpy arrays.

Diagnostic-only on public texture data. Not an authentication validator.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class StrategyResult:
    """Per-query inference output, carrying enough scoring detail for abstention."""

    predicted_class: str
    top1_score: float
    top2_score: float


def _as_array(emb: Any) -> np.ndarray:
    arr = np.asarray(emb, dtype=np.float64)
    if arr.ndim == 1:
        return arr
    if arr.ndim == 2 and arr.shape[0] == 1:
        return arr[0]
    raise ValueError(f"expected 1-D embedding, got shape {arr.shape}")


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n == 0.0:
        return v
    return v / n


def group_embeddings_by_label(
    records: list[dict],
    label_strategy: str,
    split_filter: Iterable[str] | None = None,
) -> dict[str, list[np.ndarray]]:
    """Group records by ``record[label_strategy]``, filtering by split.

    ``split_filter`` is an iterable of split names (e.g. ``{"train"}``); if
    ``None``, all splits are kept. Records whose split is not in the filter
    are dropped *before* grouping, so leakage between train/val/test never
    silently slips through.

    Raises ``ValueError`` if the filtered grouping has fewer than 2 distinct
    classes (an episode requires at least 2 classes to be meaningful).
    """
    if split_filter is not None:
        allowed = set(split_filter)
        filtered = [r for r in records if r.get("split") in allowed]
        if not filtered:
            raise ValueError(
                f"split_filter={sorted(allowed)} matched zero records "
                f"(input had {len(records)} records)"
            )
    else:
        filtered = list(records)

    grouped: dict[str, list[np.ndarray]] = {}
    for r in filtered:
        if label_strategy not in r:
            raise KeyError(f"record missing label_strategy key {label_strategy!r}")
        lbl = r[label_strategy]
        if lbl is None:
            continue
        grouped.setdefault(str(lbl), []).append(_as_array(r["embedding"]))

    if len(grouped) < 2:
        raise ValueError(
            f"label_strategy={label_strategy!r} yielded {len(grouped)} class(es) "
            f"after split_filter={split_filter}; need at least 2"
        )
    return grouped


def sample_episode(
    grouped: dict[str, list[np.ndarray]],
    ways: int | None,
    shots: int,
    query_per_class: int,
    rng: random.Random,
) -> tuple[dict[str, list[np.ndarray]], dict[str, list[np.ndarray]]] | None:
    """Sample a single N-way K-shot episode without support/query overlap.

    Returns ``(support, query)`` mappings keyed by class label, or ``None``
    when no eligible class set can supply ``shots + query_per_class`` examples.

    ``ways`` may be ``None`` to use every class that has enough examples.
    """
    eligible = [c for c, embs in grouped.items() if len(embs) >= shots + query_per_class]
    if len(eligible) < 2:
        return None

    chosen = eligible if (ways is None or ways >= len(eligible)) else rng.sample(eligible, ways)

    support: dict[str, list[np.ndarray]] = {}
    query: dict[str, list[np.ndarray]] = {}
    for cls in chosen:
        embs = list(grouped[cls])
        rng.shuffle(embs)
        support[cls] = embs[:shots]
        query[cls] = embs[shots : shots + query_per_class]
    return support, query


def prototype_centroid(support_embeddings: list[np.ndarray]) -> np.ndarray:
    """Mean of the support set, then L2-normalized."""
    if not support_embeddings:
        raise ValueError("support set is empty")
    stacked = np.stack([_as_array(e) for e in support_embeddings], axis=0)
    centroid = stacked.mean(axis=0)
    return _l2_normalize(centroid)


def prototype_medoid(support_embeddings: list[np.ndarray]) -> np.ndarray:
    """Embedding with highest mean cosine similarity to its peers (single returns itself)."""
    if not support_embeddings:
        raise ValueError("support set is empty")
    if len(support_embeddings) == 1:
        return _as_array(support_embeddings[0])
    stacked = np.stack([_as_array(e) for e in support_embeddings], axis=0)
    sims = stacked @ stacked.T
    np.fill_diagonal(sims, 0.0)
    mean_sims = sims.mean(axis=1)
    idx = int(np.argmax(mean_sims))
    return stacked[idx]


def _top_two_classes(class_scores: dict[str, float]) -> tuple[str, float, float]:
    ordered = sorted(class_scores.items(), key=lambda kv: kv[1], reverse=True)
    pred_class, top1 = ordered[0]
    top2 = ordered[1][1] if len(ordered) > 1 else 0.0
    return pred_class, float(top1), float(top2)


def nearest_neighbor_strategy(
    query_embedding: np.ndarray, support: dict[str, list[np.ndarray]]
) -> StrategyResult:
    """Single-NN classification: score per class = max cosine sim to that class."""
    q = _as_array(query_embedding)
    class_scores: dict[str, float] = {}
    for cls, embs in support.items():
        if not embs:
            continue
        stacked = np.stack([_as_array(e) for e in embs], axis=0)
        class_scores[cls] = float(np.max(stacked @ q))
    pred, t1, t2 = _top_two_classes(class_scores)
    return StrategyResult(pred, t1, t2)


def top_k_mean_strategy(
    query_embedding: np.ndarray,
    support: dict[str, list[np.ndarray]],
    k: int = 3,
) -> StrategyResult:
    """Per-class score = mean cosine sim of top-k closest support examples."""
    q = _as_array(query_embedding)
    class_scores: dict[str, float] = {}
    for cls, embs in support.items():
        if not embs:
            continue
        stacked = np.stack([_as_array(e) for e in embs], axis=0)
        sims = stacked @ q
        kk = min(k, sims.shape[0])
        top = np.partition(sims, -kk)[-kk:]
        class_scores[cls] = float(top.mean())
    pred, t1, t2 = _top_two_classes(class_scores)
    return StrategyResult(pred, t1, t2)


def prototype_centroid_strategy(
    query_embedding: np.ndarray, support: dict[str, list[np.ndarray]]
) -> StrategyResult:
    q = _as_array(query_embedding)
    class_scores: dict[str, float] = {}
    for cls, embs in support.items():
        if not embs:
            continue
        proto = prototype_centroid(embs)
        class_scores[cls] = float(proto @ q)
    pred, t1, t2 = _top_two_classes(class_scores)
    return StrategyResult(pred, t1, t2)


def prototype_medoid_strategy(
    query_embedding: np.ndarray, support: dict[str, list[np.ndarray]]
) -> StrategyResult:
    q = _as_array(query_embedding)
    class_scores: dict[str, float] = {}
    for cls, embs in support.items():
        if not embs:
            continue
        proto = prototype_medoid(embs)
        class_scores[cls] = float(proto @ q)
    pred, t1, t2 = _top_two_classes(class_scores)
    return StrategyResult(pred, t1, t2)


def evaluate_with_abstention_curve(
    query_results: list[tuple[str, str, float, float]],
    score_thresholds: list[float],
    margin_thresholds: list[float],
) -> list[dict]:
    """Sweep (score_threshold, margin_threshold) and return a flat list of records.

    Each input tuple is ``(true_class, predicted_class, top1_score, top2_score)``.
    For each threshold pair we compute:
      - ``abstention_rate`` = fraction abstained
      - ``coverage`` = 1 - abstention_rate
      - ``accuracy_after_abstention`` = accuracy among non-abstained queries
      - ``correct_after_abstention`` / ``total_after_abstention`` (for traceability)

    Output is a list of dicts (pandas-friendly), one record per threshold
    pair, with ``score_threshold`` and ``margin_threshold`` as primary keys.
    """
    n = len(query_results)
    out: list[dict] = []
    for s_thr in score_thresholds:
        for m_thr in margin_thresholds:
            kept_correct = 0
            kept_total = 0
            for true_c, pred_c, t1, t2 in query_results:
                if t1 < s_thr or (t1 - t2) < m_thr:
                    continue
                kept_total += 1
                if pred_c == true_c:
                    kept_correct += 1
            abst_rate = (n - kept_total) / n if n > 0 else 0.0
            acc = kept_correct / kept_total if kept_total > 0 else 0.0
            out.append(
                {
                    "score_threshold": float(s_thr),
                    "margin_threshold": float(m_thr),
                    "abstention_rate": float(abst_rate),
                    "coverage": float(1.0 - abst_rate),
                    "accuracy_after_abstention": float(acc),
                    "correct_after_abstention": int(kept_correct),
                    "total_after_abstention": int(kept_total),
                    "n_queries": int(n),
                }
            )
    return out


def support_set_variance(per_episode_accuracies: list[float]) -> dict[str, float]:
    """Mean, std, and 5th/95th percentile of per-episode accuracy."""
    if not per_episode_accuracies:
        return {"mean": 0.0, "std": 0.0, "p05": 0.0, "p95": 0.0, "n": 0}
    arr = np.asarray(per_episode_accuracies, dtype=np.float64)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=0)),
        "p05": float(np.percentile(arr, 5.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "n": int(arr.shape[0]),
    }


STRATEGIES = {
    "nearest_neighbor": lambda q, s, **_: nearest_neighbor_strategy(q, s),
    "top_k_mean": lambda q, s, **kw: top_k_mean_strategy(q, s, k=kw.get("k", 3)),
    "prototype_centroid": lambda q, s, **_: prototype_centroid_strategy(q, s),
    "prototype_medoid": lambda q, s, **_: prototype_medoid_strategy(q, s),
    "prototype_centroid_with_abstention": lambda q, s, **_: prototype_centroid_strategy(q, s),
}


def run_episode(
    support: dict[str, list[np.ndarray]],
    query: dict[str, list[np.ndarray]],
    strategy: str,
    *,
    top_k_for_mean: int = 3,
) -> tuple[float, list[tuple[str, str, float, float]]]:
    """Score every query against ``support`` using ``strategy``.

    Returns ``(accuracy, per_query_records)`` where each record is
    ``(true_class, predicted_class, top1_score, top2_score)``.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; known: {sorted(STRATEGIES)}")
    fn = STRATEGIES[strategy]
    records: list[tuple[str, str, float, float]] = []
    correct = 0
    total = 0
    for true_c, queries in query.items():
        for q_emb in queries:
            res = fn(q_emb, support, k=top_k_for_mean)
            records.append((true_c, res.predicted_class, res.top1_score, res.top2_score))
            if res.predicted_class == true_c:
                correct += 1
            total += 1
    acc = correct / total if total > 0 else 0.0
    return acc, records
