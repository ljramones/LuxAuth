"""Event envelope model and event type constants."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class EventTypes:
    """String constants for all platform event types."""

    SCAN_CREATED = "scan.created"
    SCAN_RECIPE_RESOLVED = "scan.recipe_resolved"
    SCAN_STATUS_CHANGED = "scan.status_changed"
    IMAGE_UPLOADED = "image.uploaded"
    IMAGE_QUALITY_COMPLETED = "image.quality_completed"
    IMAGE_NORMALIZED = "image.normalized"
    EMBEDDING_GENERATED = "embedding.generated"
    VECTOR_SEARCH_COMPLETED = "vector_search.completed"
    REGION_SCORED = "region.scored"
    AUTHENTICATION_DECISION_CREATED = "authentication_decision.created"
    CERTIFICATE_ISSUED = "certificate.issued"
    EXPERT_REVIEW_RECORDED = "expert_review.recorded"
    PROCESSING_FAILED = "processing.failed"


class EventEnvelope(BaseModel):
    """Standard envelope for all asynchronous messages on SQS."""

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str
    correlation_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    scan_session_id: uuid.UUID | None = None
    image_id: uuid.UUID | None = None
    region_code: str | None = None
    source_service: str | None = None
    schema_version: str = "1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict = Field(default_factory=dict)  # type: ignore[type-arg]
