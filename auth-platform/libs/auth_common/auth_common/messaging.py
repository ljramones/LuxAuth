"""SQS messaging helpers via boto3 (LocalStack-compatible)."""

from __future__ import annotations

import json
from typing import Any

import boto3

from auth_common.events import EventEnvelope

_sqs_client: Any | None = None
_queue_url_cache: dict[str, str] = {}


def get_sqs_client() -> Any:
    """Return a cached boto3 SQS client configured for the current settings."""
    global _sqs_client  # noqa: PLW0603
    if _sqs_client is None:
        from auth_common.config import Settings

        settings = Settings()
        _sqs_client = boto3.client(
            "sqs",
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
        )
    return _sqs_client


def get_queue_url(queue_name: str) -> str:
    """Resolve and cache the queue URL for the given queue name."""
    if queue_name not in _queue_url_cache:
        client = get_sqs_client()
        response = client.get_queue_url(QueueName=queue_name)
        _queue_url_cache[queue_name] = response["QueueUrl"]
    return _queue_url_cache[queue_name]


def send_message(queue_name: str, message: EventEnvelope) -> None:
    """Serialize an EventEnvelope to JSON and send it to the named SQS queue."""
    client = get_sqs_client()
    queue_url = get_queue_url(queue_name)
    client.send_message(
        QueueUrl=queue_url,
        MessageBody=message.model_dump_json(),
    )


def receive_messages(
    queue_name: str,
    max_messages: int = 1,
    wait_time: int = 5,
) -> list[EventEnvelope]:
    """Receive up to max_messages from the named SQS queue, returned as EventEnvelopes."""
    client = get_sqs_client()
    queue_url = get_queue_url(queue_name)
    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time,
    )
    envelopes: list[EventEnvelope] = []
    for msg in response.get("Messages", []):
        body = json.loads(msg["Body"])
        envelope = EventEnvelope.model_validate(body)
        # Stash the receipt handle so callers can delete after processing
        envelope._receipt_handle = msg["ReceiptHandle"]  # type: ignore[attr-defined]
        envelopes.append(envelope)
    return envelopes


def delete_message(queue_name: str, receipt_handle: str) -> None:
    """Delete a processed message from the named SQS queue."""
    client = get_sqs_client()
    queue_url = get_queue_url(queue_name)
    client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle,
    )
