"""Structured JSON logging via structlog."""

from __future__ import annotations

import logging
import sys

import structlog

from auth_common.correlation import get_correlation_id


def _add_correlation_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Inject the current correlation_id into every log entry."""
    correlation_id = get_correlation_id()
    if correlation_id is not None:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON output at the given level."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            _add_correlation_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        root_logger.addHandler(handler)


def get_logger(service_name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound with the given service name."""
    configure_logging()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(service=service_name)
    return logger
