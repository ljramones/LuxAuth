"""Correlation ID middleware and accessor for FastAPI."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return the current correlation ID from context, or None."""
    return _correlation_id_ctx.get()


def set_correlation_id(value: str) -> None:
    """Explicitly set the correlation ID in the current context."""
    _correlation_id_ctx.set(value)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Extract or generate a correlation ID for every request."""

    def __init__(self, app, header_name: str = "X-Correlation-ID") -> None:  # noqa: ANN001
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        _correlation_id_ctx.set(correlation_id)

        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response
