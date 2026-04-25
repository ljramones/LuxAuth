"""Unit tests for region scoring decision logic."""



# The handler uses these thresholds:
#   authentic >= 0.85 and counterfeit < 0.50 → STRONG_MATCH
#   authentic >= 0.70                        → MODERATE_MATCH
#   authentic >= 0.50                        → WEAK_MATCH
#   counterfeit > authentic                  → MISMATCH
#   else                                     → INCONCLUSIVE


def _classify(authentic: float, counterfeit: float) -> str:
    """Mirror the classification logic from handlers.score_region."""
    if authentic >= 0.85 and counterfeit < 0.50:
        return "STRONG_MATCH"
    elif authentic >= 0.70:
        return "MODERATE_MATCH"
    elif authentic >= 0.50:
        return "WEAK_MATCH"
    elif counterfeit > authentic:
        return "MISMATCH"
    else:
        return "INCONCLUSIVE"


class TestRegionDecisionLogic:
    def test_strong_match(self):
        assert _classify(0.90, 0.30) == "STRONG_MATCH"

    def test_strong_match_boundary(self):
        assert _classify(0.85, 0.49) == "STRONG_MATCH"

    def test_high_authentic_but_high_counterfeit_is_moderate(self):
        """authentic >= 0.85 but counterfeit >= 0.50 falls to MODERATE_MATCH."""
        assert _classify(0.90, 0.55) == "MODERATE_MATCH"

    def test_moderate_match(self):
        assert _classify(0.75, 0.40) == "MODERATE_MATCH"

    def test_moderate_match_boundary(self):
        assert _classify(0.70, 0.60) == "MODERATE_MATCH"

    def test_weak_match(self):
        assert _classify(0.55, 0.30) == "WEAK_MATCH"

    def test_weak_match_boundary(self):
        assert _classify(0.50, 0.40) == "WEAK_MATCH"

    def test_mismatch_counterfeit_exceeds_authentic(self):
        assert _classify(0.30, 0.80) == "MISMATCH"

    def test_mismatch_low_scores(self):
        assert _classify(0.10, 0.20) == "MISMATCH"

    def test_inconclusive_equal_low_scores(self):
        assert _classify(0.40, 0.40) == "INCONCLUSIVE"

    def test_inconclusive_low_authentic(self):
        assert _classify(0.30, 0.10) == "INCONCLUSIVE"

    def test_perfect_authentic(self):
        assert _classify(1.0, 0.0) == "STRONG_MATCH"

    def test_zero_scores(self):
        assert _classify(0.0, 0.0) == "INCONCLUSIVE"
