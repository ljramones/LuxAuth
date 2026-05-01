"""Embedder backends for the embedding-service.

Each module exposes a single function that maps normalized image bytes to a
list[float] embedding. Backends are dispatched by ``embedding_model_version``
in ``app.handlers``.
"""
