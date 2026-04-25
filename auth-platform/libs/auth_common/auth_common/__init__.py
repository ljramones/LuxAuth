"""auth-common: Shared library for the luxury authentication platform."""

from auth_common.config import Settings
from auth_common.correlation import CorrelationMiddleware, get_correlation_id
from auth_common.database import get_db, get_engine, get_session_factory
from auth_common.events import EventEnvelope, EventTypes
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
]
