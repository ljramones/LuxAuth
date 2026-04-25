"""Unit tests for the decision handler's result classification logic.

Tests the decision rules extracted from handlers.make_decision without
needing a database connection.
"""


def _decide(
    required_regions: list[str],
    scored_regions: dict[str, dict],
) -> tuple[str, str]:
    """
    Mirror the decision logic from handlers.make_decision.

    scored_regions maps region_code -> {
        "authentic_similarity": float,
        "counterfeit_similarity": float,
        "region_decision": str,
    }

    Returns (result, result_reason).
    """
    scored_set = set(scored_regions.keys())
    missing_regions = [r for r in required_regions if r not in scored_set]
    all_required_satisfied = len(missing_regions) == 0 and len(required_regions) > 0

    rows = list(scored_regions.values())

    if rows:
        authentic_scores = [r["authentic_similarity"] for r in rows]
        counterfeit_scores = [r["counterfeit_similarity"] for r in rows]
        decisions = [r["region_decision"] for r in rows]
        avg_authentic = sum(authentic_scores) / len(authentic_scores)
        avg_counterfeit = sum(counterfeit_scores) / len(counterfeit_scores)
        any_mismatch = any(d == "MISMATCH" for d in decisions)
        all_strong = all(d == "STRONG_MATCH" for d in decisions)
    else:
        avg_authentic = 0.0
        avg_counterfeit = 0.0
        any_mismatch = False
        all_strong = False

    if not all_required_satisfied:
        return "INCONCLUSIVE", "MISSING_REQUIRED_REGIONS"
    elif not rows:
        return "INCONCLUSIVE", "NO_REGION_SCORES"
    elif any_mismatch:
        return "UNVERIFIED", "REGION_MISMATCH_DETECTED"
    elif avg_counterfeit > avg_authentic:
        return "UNVERIFIED", "COUNTERFEIT_SIMILARITY_EXCEEDS_AUTHENTIC"
    elif all_strong and avg_authentic >= 0.85 and avg_counterfeit < 0.40:
        return "VERIFIED", "ALL_REGIONS_STRONG_MATCH"
    elif avg_authentic >= 0.60:
        return "EXPERT_REVIEW_REQUIRED", "MODERATE_MATCH_REQUIRES_REVIEW"
    else:
        return "INCONCLUSIVE", "INSUFFICIENT_SIMILARITY"


ALL_REGIONS = [
    "EXTERIOR_CANVAS",
    "FRONT_LOGO_PRINT",
    "INTERIOR_HEAT_STAMP",
    "HARDWARE_ENGRAVING",
    "STITCHING_DETAIL",
]


def _strong_region():
    return {"authentic_similarity": 0.92, "counterfeit_similarity": 0.20, "region_decision": "STRONG_MATCH"}


def _mismatch_region():
    return {"authentic_similarity": 0.30, "counterfeit_similarity": 0.80, "region_decision": "MISMATCH"}


def _moderate_region():
    return {"authentic_similarity": 0.75, "counterfeit_similarity": 0.35, "region_decision": "MODERATE_MATCH"}


class TestDecisionRules:
    def test_verified_all_strong(self):
        scores = {r: _strong_region() for r in ALL_REGIONS}
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "VERIFIED"
        assert reason == "ALL_REGIONS_STRONG_MATCH"

    def test_inconclusive_missing_regions(self):
        """Only 1 of 5 regions scored → INCONCLUSIVE."""
        scores = {"EXTERIOR_CANVAS": _strong_region()}
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "INCONCLUSIVE"
        assert reason == "MISSING_REQUIRED_REGIONS"

    def test_inconclusive_no_regions_scored(self):
        result, reason = _decide(ALL_REGIONS, {})
        assert result == "INCONCLUSIVE"
        assert reason == "MISSING_REQUIRED_REGIONS"

    def test_inconclusive_no_required_and_no_scores(self):
        """No required regions and no scores → falls through."""
        result, reason = _decide([], {})
        assert result == "INCONCLUSIVE"
        assert reason == "MISSING_REQUIRED_REGIONS"

    def test_unverified_mismatch(self):
        scores = {r: _strong_region() for r in ALL_REGIONS}
        scores["HARDWARE_ENGRAVING"] = _mismatch_region()
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "UNVERIFIED"
        assert reason == "REGION_MISMATCH_DETECTED"

    def test_unverified_counterfeit_exceeds_authentic(self):
        high_counterfeit = {
            "authentic_similarity": 0.40,
            "counterfeit_similarity": 0.80,
            "region_decision": "WEAK_MATCH",
        }
        scores = {r: high_counterfeit for r in ALL_REGIONS}
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "UNVERIFIED"
        assert reason == "COUNTERFEIT_SIMILARITY_EXCEEDS_AUTHENTIC"

    def test_expert_review_moderate_scores(self):
        scores = {r: _moderate_region() for r in ALL_REGIONS}
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "EXPERT_REVIEW_REQUIRED"
        assert reason == "MODERATE_MATCH_REQUIRES_REVIEW"

    def test_inconclusive_insufficient_similarity(self):
        low = {"authentic_similarity": 0.40, "counterfeit_similarity": 0.30, "region_decision": "INCONCLUSIVE"}
        scores = {r: low for r in ALL_REGIONS}
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "INCONCLUSIVE"
        assert reason == "INSUFFICIENT_SIMILARITY"

    def test_verified_requires_all_strong_and_thresholds(self):
        """All STRONG_MATCH but high counterfeit avg → EXPERT_REVIEW."""
        borderline = {
            "authentic_similarity": 0.90,
            "counterfeit_similarity": 0.45,
            "region_decision": "STRONG_MATCH",
        }
        scores = {r: borderline for r in ALL_REGIONS}
        result, reason = _decide(ALL_REGIONS, scores)
        # avg_counterfeit = 0.45 >= 0.40, so not VERIFIED
        assert result == "EXPERT_REVIEW_REQUIRED"

    def test_two_of_five_regions_still_inconclusive(self):
        scores = {
            "EXTERIOR_CANVAS": _strong_region(),
            "FRONT_LOGO_PRINT": _strong_region(),
        }
        result, reason = _decide(ALL_REGIONS, scores)
        assert result == "INCONCLUSIVE"
        assert reason == "MISSING_REQUIRED_REGIONS"
