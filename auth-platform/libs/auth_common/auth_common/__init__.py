"""auth-common: Shared library for the luxury authentication platform."""

from auth_common.audit import record_audit_event
from auth_common.config import Settings
from auth_common.correlation import CorrelationMiddleware, get_correlation_id
from auth_common.database import get_db, get_engine, get_session_factory
from auth_common.events import EventEnvelope, EventTypes
from auth_common.idempotency import (
    check_idempotency,
    make_idempotency_key,
    record_processing_complete,
    record_processing_failed,
    record_processing_start,
)
from auth_common.imaging import compute_quality_metrics, compute_texture_embedding, normalize_image, validate_image
from auth_common.logging import get_logger
from auth_common.models import (
    AuditEvent,
    AuthenticationDecision,
    CertificateResponse,
    DeviceRegister,
    DeviceResponse,
    EmbeddingRecord,
    ImageAssetResponse,
    ImageQualityReport,
    NormalizationResult,
    RegionScore,
    ReviewCase,
    ScanRecipeRegion,
    ScanRecipeResponse,
    ScanSessionCreate,
    ScanSessionResponse,
    VectorSearchResult,
)
from auth_common.regions import RegionCodes
from auth_common.worker import run_worker

__all__ = [
    "Settings",
    "CorrelationMiddleware",
    "get_correlation_id",
    "get_db",
    "get_engine",
    "get_session_factory",
    "EventEnvelope",
    "EventTypes",
    "get_logger",
    "AuditEvent",
    "AuthenticationDecision",
    "CertificateResponse",
    "DeviceRegister",
    "DeviceResponse",
    "EmbeddingRecord",
    "ImageAssetResponse",
    "ImageQualityReport",
    "NormalizationResult",
    "RegionScore",
    "ReviewCase",
    "ScanRecipeRegion",
    "ScanRecipeResponse",
    "ScanSessionCreate",
    "ScanSessionResponse",
    "VectorSearchResult",
    "RegionCodes",
    "record_audit_event",
    "check_idempotency",
    "make_idempotency_key",
    "record_processing_start",
    "record_processing_complete",
    "record_processing_failed",
    "run_worker",
    "validate_image",
    "compute_quality_metrics",
    "normalize_image",
    "compute_texture_embedding",
]
