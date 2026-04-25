"""Reusable SQS worker loop for pipeline services."""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import Awaitable, Callable
from typing import Any

from auth_common.correlation import set_correlation_id
from auth_common.events import EventEnvelope
from auth_common.logging import get_logger
from auth_common.messaging import delete_message, receive_messages

logger = get_logger("worker")


async def run_worker(
    queue_name: str,
    handler: Callable[[EventEnvelope], Awaitable[Any]],
    *,
    service_name: str = "worker",
    poll_interval: float = 1.0,
    max_messages: int = 1,
    wait_time: int = 5,
) -> None:
    """Poll an SQS queue and invoke handler for each message.

    Runs forever. On handler success, deletes the message.
    On handler failure, logs the error and leaves the message
    for retry/DLQ via SQS visibility timeout.
    """
    svc_logger = get_logger(service_name)
    svc_logger.info("worker_starting", queue=queue_name)

    while True:
        try:
            messages = receive_messages(
                queue_name,
                max_messages=max_messages,
                wait_time=wait_time,
            )
        except Exception:
            svc_logger.warning("queue_poll_error", queue=queue_name)
            await asyncio.sleep(poll_interval)
            continue

        for envelope in messages:
            # Set correlation ID for this processing context
            if envelope.correlation_id:
                set_correlation_id(str(envelope.correlation_id))

            receipt = getattr(envelope, "_receipt_handle", None)
            try:
                svc_logger.info(
                    "processing_message",
                    event_type=envelope.event_type,
                    event_id=str(envelope.event_id),
                    image_id=str(envelope.image_id) if envelope.image_id else None,
                    scan_session_id=str(envelope.scan_session_id) if envelope.scan_session_id else None,
                )
                await handler(envelope)

                if receipt:
                    delete_message(queue_name, receipt)
                svc_logger.info("message_processed", event_id=str(envelope.event_id))

            except Exception as exc:
                svc_logger.error(
                    "message_processing_failed",
                    event_id=str(envelope.event_id),
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
                # Don't delete — let SQS retry / send to DLQ

        if not messages:
            await asyncio.sleep(poll_interval)
