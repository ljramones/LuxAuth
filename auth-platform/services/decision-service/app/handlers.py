import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.audit import record_audit_event
from auth_common.logging import get_logger
from auth_common.models import AuthenticationDecision

from app.settings import settings

logger = get_logger(settings.service_name)

DECISION_RULE_VERSION = "decision_rules_v0.2.0"
EMBEDDING_MODEL_VERSION = "stub_embedder_v0.1.0"
REFERENCE_DATASET_VERSION = "seed_v0.1.0"


async def make_decision(
    scan_session_id: str,
    db_session: AsyncSession,
) -> AuthenticationDecision:
    """Aggregate region scores and produce an authentication decision."""

    # Check if decision already exists
    existing = await db_session.execute(
        text("SELECT result, summary, region_results, decision_rule_version, embedding_model_version, reference_dataset_version FROM authentication_decisions WHERE scan_session_id = :sid"),
        {"sid": scan_session_id},
    )
    existing_row = existing.mappings().first()
    if existing_row:
        return AuthenticationDecision(
            scan_session_id=scan_session_id,
            result=existing_row["result"],
            summary=existing_row["summary"] if isinstance(existing_row["summary"], dict) else json.loads(existing_row["summary"]),
            region_results=existing_row["region_results"] if isinstance(existing_row["region_results"], list) else json.loads(existing_row["region_results"]),
            decision_rule_version=existing_row["decision_rule_version"],
            embedding_model_version=existing_row["embedding_model_version"],
            reference_dataset_version=existing_row["reference_dataset_version"],
        )

    # Fetch scan session to get recipe
    session_result = await db_session.execute(
        text("SELECT scan_recipe_id FROM scan_sessions WHERE id = :sid"),
        {"sid": scan_session_id},
    )
    session_row = session_result.mappings().first()
    if not session_row:
        raise HTTPException(status_code=404, detail="Scan session not found")

    # Fetch required regions from recipe
    required_regions: list[str] = []
    if session_row["scan_recipe_id"]:
        rr_result = await db_session.execute(
            text(
                "SELECT region_code FROM scan_recipe_regions "
                "WHERE scan_recipe_id = :rid ORDER BY sort_order"
            ),
            {"rid": str(session_row["scan_recipe_id"])},
        )
        required_regions = [r["region_code"] for r in rr_result.mappings()]

    # Fetch all region scores for this scan session
    result = await db_session.execute(
        text("SELECT * FROM region_scores WHERE scan_session_id = :sid"),
        {"sid": scan_session_id},
    )
    rows = result.mappings().all()

    # Build scored regions set
    scored_regions = {r["region_code"] for r in rows}
    missing_regions = [r for r in required_regions if r not in scored_regions]
    all_required_satisfied = len(missing_regions) == 0 and len(required_regions) > 0

    # Compute score aggregates (may be empty)
    if rows:
        authentic_scores = [float(r["authentic_similarity"]) for r in rows]
        counterfeit_scores = [float(r["counterfeit_similarity"]) for r in rows]
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

    # Determine result with completeness checks
    if not all_required_satisfied:
        decision_result = "INCONCLUSIVE"
        result_reason = "MISSING_REQUIRED_REGIONS"
    elif not rows:
        decision_result = "INCONCLUSIVE"
        result_reason = "NO_REGION_SCORES"
    elif any_mismatch:
        decision_result = "UNVERIFIED"
        result_reason = "REGION_MISMATCH_DETECTED"
    elif avg_counterfeit > avg_authentic:
        decision_result = "UNVERIFIED"
        result_reason = "COUNTERFEIT_SIMILARITY_EXCEEDS_AUTHENTIC"
    elif all_strong and avg_authentic >= 0.85 and avg_counterfeit < 0.40:
        decision_result = "VERIFIED"
        result_reason = "ALL_REGIONS_STRONG_MATCH"
    elif avg_authentic >= 0.60:
        decision_result = "EXPERT_REVIEW_REQUIRED"
        result_reason = "MODERATE_MATCH_REQUIRES_REVIEW"
    else:
        decision_result = "INCONCLUSIVE"
        result_reason = "INSUFFICIENT_SIMILARITY"

    summary = {
        "required_region_count": len(required_regions),
        "completed_region_count": len(scored_regions & set(required_regions)),
        "missing_regions": missing_regions,
        "all_required_regions_satisfied": all_required_satisfied,
        "avg_authentic_similarity": round(avg_authentic, 4),
        "avg_counterfeit_similarity": round(avg_counterfeit, 4),
        "region_count": len(rows),
        "any_mismatch": any_mismatch,
        "all_strong": all_strong,
        "result_reason": result_reason,
    }

    region_results = [
        {
            "region_code": r["region_code"],
            "region_decision": r["region_decision"],
            "authentic_similarity": float(r["authentic_similarity"]),
            "counterfeit_similarity": float(r["counterfeit_similarity"]),
        }
        for r in rows
    ]

    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Insert into authentication_decisions table
    await db_session.execute(
        text(
            """
            INSERT INTO authentication_decisions (
                id, scan_session_id, result, summary, region_results,
                decision_rule_version, embedding_model_version,
                reference_dataset_version, created_at
            ) VALUES (
                :id, :scan_session_id, :result, :summary, :region_results,
                :decision_rule_version, :embedding_model_version,
                :reference_dataset_version, :created_at
            )
            """
        ),
        {
            "id": decision_id,
            "scan_session_id": scan_session_id,
            "result": decision_result,
            "summary": json.dumps(summary),
            "region_results": json.dumps(region_results),
            "decision_rule_version": DECISION_RULE_VERSION,
            "embedding_model_version": EMBEDDING_MODEL_VERSION,
            "reference_dataset_version": REFERENCE_DATASET_VERSION,
            "created_at": now,
        },
    )

    # Update scan session status to match decision
    await db_session.execute(
        text("UPDATE scan_sessions SET status = :status, updated_at = :now WHERE id = :sid"),
        {"status": decision_result, "sid": scan_session_id, "now": now},
    )

    await record_audit_event(
        db_session,
        "DECISION_CREATED",
        scan_session_id=uuid.UUID(scan_session_id),
        payload={"result": decision_result, "result_reason": result_reason},
    )

    await db_session.commit()

    logger.info(
        "decision_made",
        decision_id=decision_id,
        scan_session_id=scan_session_id,
        result=decision_result,
        result_reason=result_reason,
    )

    return AuthenticationDecision(
        scan_session_id=scan_session_id,
        result=decision_result,
        summary=summary,
        region_results=region_results,
        decision_rule_version=DECISION_RULE_VERSION,
        embedding_model_version=EMBEDDING_MODEL_VERSION,
        reference_dataset_version=REFERENCE_DATASET_VERSION,
    )
