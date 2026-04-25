"""Pydantic models shared across platform services."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Scan sessions
# ---------------------------------------------------------------------------

class ScanSessionCreate(BaseModel):
    claimed_brand: str
    claimed_category: str
    claimed_material: str
    claimed_model: str | None = None
    device_id: UUID
    operator_id: UUID | None = None
    organization_id: UUID


class ScanSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    claimed_brand: str
    claimed_category: str
    claimed_material: str
    claimed_model: str | None = None
    scan_recipe_id: UUID | None = None
    required_regions: list[str] = []
    created_at: datetime


# ---------------------------------------------------------------------------
# Scan recipes
# ---------------------------------------------------------------------------

class ScanRecipeRegion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_code: str
    display_name: str
    min_images: int
    magnification_profile: str
    lighting_profile: str


class ScanRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recipe_key: str
    brand: str
    category: str
    material: str
    version: int
    regions: list[ScanRecipeRegion] = []


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

class DeviceRegister(BaseModel):
    device_serial: str
    device_type: str
    organization_id: UUID
    firmware_version: str | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_serial: str
    device_type: str
    status: str
    firmware_version: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Image assets
# ---------------------------------------------------------------------------

class ImageAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_session_id: UUID
    region_code: str
    raw_object_uri: str
    checksum: str
    file_size_bytes: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Image quality
# ---------------------------------------------------------------------------

class ImageQualityReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_asset_id: UUID
    sharpness_score: float
    exposure_score: float
    glare_score: float
    quality_status: str
    issues: list[str] = []


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

class NormalizationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_asset_id: UUID
    normalized_object_uri: str
    preprocessing_version: str


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

class EmbeddingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_asset_id: UUID
    embedding: list[float]
    embedding_model_version: str


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------

class VectorSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_asset_id: UUID
    nearest_authentic: list[dict] = []  # type: ignore[type-arg]
    nearest_counterfeit: list[dict] = []  # type: ignore[type-arg]
    authentic_cluster_score: float
    counterfeit_cluster_score: float
    ood_score: float


# ---------------------------------------------------------------------------
# Region scoring
# ---------------------------------------------------------------------------

class RegionScore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_asset_id: UUID
    scan_session_id: UUID
    region_code: str
    authentic_similarity: float
    counterfeit_similarity: float
    ood_score: float
    region_decision: str


# ---------------------------------------------------------------------------
# Authentication decision
# ---------------------------------------------------------------------------

class AuthenticationDecision(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_session_id: UUID
    result: str
    summary: dict  # type: ignore[type-arg]
    region_results: list[dict] = []  # type: ignore[type-arg]
    decision_rule_version: str
    embedding_model_version: str
    reference_dataset_version: str


# ---------------------------------------------------------------------------
# Expert review
# ---------------------------------------------------------------------------

class ReviewCase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_session_id: UUID
    status: str
    reviewer_notes: str | None = None
    reviewer_decision: str | None = None


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    certificate_number: str
    scan_session_id: UUID
    brand: str
    category: str
    material: str
    issued_at: datetime
    status: str


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    event_type: str
    correlation_id: UUID | None = None
    tenant_id: UUID | None = None
    scan_session_id: UUID | None = None
    image_id: UUID | None = None
    actor_id: UUID | None = None
    payload: dict | None = None  # type: ignore[type-arg]
