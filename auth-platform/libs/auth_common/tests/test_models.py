"""Unit tests for shared Pydantic models."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from auth_common.models import (
    AuthenticationDecision,
    ImageQualityReport,
    RegionScore,
    ScanRecipeRegion,
    ScanRecipeResponse,
    ScanSessionCreate,
    ScanSessionResponse,
    VectorSearchResult,
)


class TestScanSessionCreate:
    def test_valid_creation(self):
        m = ScanSessionCreate(
            claimed_brand="Louis Vuitton",
            claimed_category="handbag",
            claimed_material="monogram_canvas",
            device_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
        )
        assert m.claimed_brand == "Louis Vuitton"
        assert m.claimed_model is None

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ScanSessionCreate(
                claimed_brand="Louis Vuitton",
                claimed_category="handbag",
                # missing claimed_material, device_id, organization_id
            )

    def test_optional_model(self):
        m = ScanSessionCreate(
            claimed_brand="Gucci",
            claimed_category="wallet",
            claimed_material="leather",
            claimed_model="GG Marmont",
            device_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
        )
        assert m.claimed_model == "GG Marmont"


class TestScanSessionResponse:
    def test_defaults(self):
        m = ScanSessionResponse(
            id=uuid.uuid4(),
            status="CREATED",
            claimed_brand="Louis Vuitton",
            claimed_category="handbag",
            claimed_material="monogram_canvas",
            created_at=datetime.now(timezone.utc),
        )
        assert m.required_regions == []
        assert m.scan_recipe_id is None

    def test_with_regions(self):
        m = ScanSessionResponse(
            id=uuid.uuid4(),
            status="CREATED",
            claimed_brand="Louis Vuitton",
            claimed_category="handbag",
            claimed_material="monogram_canvas",
            required_regions=["EXTERIOR_CANVAS", "FRONT_LOGO_PRINT"],
            scan_recipe_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        assert len(m.required_regions) == 2


class TestRegionScore:
    def test_valid(self):
        m = RegionScore(
            image_asset_id=uuid.uuid4(),
            scan_session_id=uuid.uuid4(),
            region_code="EXTERIOR_CANVAS",
            authentic_similarity=0.92,
            counterfeit_similarity=0.20,
            ood_score=0.10,
            region_decision="STRONG_MATCH",
        )
        assert m.region_decision == "STRONG_MATCH"

    def test_invalid_similarity_type(self):
        with pytest.raises(ValidationError):
            RegionScore(
                image_asset_id=uuid.uuid4(),
                scan_session_id=uuid.uuid4(),
                region_code="EXTERIOR_CANVAS",
                authentic_similarity="not_a_number",
                counterfeit_similarity=0.20,
                ood_score=0.10,
                region_decision="STRONG_MATCH",
            )


class TestAuthenticationDecision:
    def test_valid(self):
        m = AuthenticationDecision(
            scan_session_id=uuid.uuid4(),
            result="VERIFIED",
            summary={"result_reason": "ALL_REGIONS_STRONG_MATCH"},
            region_results=[],
            decision_rule_version="decision_rules_v0.2.0",
            embedding_model_version="stub_embedder_v0.1.0",
            reference_dataset_version="seed_v0.1.0",
        )
        assert m.result == "VERIFIED"

    def test_with_region_results(self):
        m = AuthenticationDecision(
            scan_session_id=uuid.uuid4(),
            result="INCONCLUSIVE",
            summary={"missing_regions": ["HARDWARE_ENGRAVING"]},
            region_results=[
                {"region_code": "EXTERIOR_CANVAS", "region_decision": "STRONG_MATCH"}
            ],
            decision_rule_version="v1",
            embedding_model_version="v1",
            reference_dataset_version="v1",
        )
        assert len(m.region_results) == 1


class TestScanRecipeResponse:
    def test_with_regions(self):
        region = ScanRecipeRegion(
            region_code="EXTERIOR_CANVAS",
            display_name="Exterior Canvas",
            min_images=1,
            magnification_profile="standard",
            lighting_profile="diffuse",
        )
        m = ScanRecipeResponse(
            id=uuid.uuid4(),
            recipe_key="louis_vuitton__handbag__monogram_canvas",
            brand="Louis Vuitton",
            category="handbag",
            material="monogram_canvas",
            version=1,
            regions=[region],
        )
        assert len(m.regions) == 1
        assert m.regions[0].region_code == "EXTERIOR_CANVAS"


class TestVectorSearchResult:
    def test_defaults(self):
        m = VectorSearchResult(
            image_asset_id=uuid.uuid4(),
            authentic_cluster_score=0.85,
            counterfeit_cluster_score=0.35,
            ood_score=0.15,
        )
        assert m.nearest_authentic == []
        assert m.nearest_counterfeit == []
