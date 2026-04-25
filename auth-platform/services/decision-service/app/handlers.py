import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.logging import get_logger
from auth_common.models import AuthenticationDecision

from app.settings import settings

logger = get_logger(settings.service_name)

DECISION_RULE_VERSION = "decision_rules_v0.1.0"
EMBEDDING_MODEL_VERSION = "stub_embedder_v0.1.0"
REFERENCE_DATASET_VERSION = "seed_v0.1.0"


async def make_decision(
    scan_session_id: str,
    db_session: AsyncSession,
) -> AuthenticationDecision:
    """Aggregate region scores and produce an authentication decision."""

    # Fetch all region scores for this scan session
    result = await db_session.execute(
        text("SELECT * FROM region_scores WHERE scan_session_id = :sid"),
        {"sid": scan_session_id},
    )
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No region scores found for scan session {scan_session_id}",
        )

    # Compute aggregates
    authentic_scores = [float(r["authentic_similarity"]) for r in rows]
    counterfeit_scores = [float(r["counterfeit_similarity"]) for r in rows]
    decisions = [r["region_decision"] for r in rows]

    avg_authentic = sum(authentic_scores) / len(authentic_scores)
    avg_counterfeit = sum(counterfeit_scores) / len(counterfeit_scores)
    any_mismatch = any(d == "MISMATCH" for d in decisions)
    all_strong = all(d == "STRONG_MATCH" for d in decisions)

    # Determine result
    if all_strong and avg_authentic >= 0.85 and avg_counterfeit < 0.40:
        decision_result = "VERIFIED"
    elif any_mismatch or avg_counterfeit > avg_authentic:
        decision_result = "UNVERIFIED"
    elif avg_authentic >= 0.60 and not all_strong:
        decision_result = "EXPERT_REVIEW_REQUIRED"
    else:
        decision_result = "INCONCLUSIVE"

    summary = {
        "avg_authentic_similarity": round(avg_authentic, 4),
        "avg_counterfeit_similarity": round(avg_counterfeit, 4),
        "region_count": len(rows),
        "any_mismatch": any_mismatch,
        "all_strong": all_strong,
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

    # Update scan session status
    await db_session.execute(
        text("UPDATE scan_sessions SET status = 'COMPLETE' WHERE id = :sid"),
        {"sid": scan_session_id},
    )
    await db_session.commit()

    decision = AuthenticationDecision(
        scan_session_id=scan_session_id,
        result=decision_result,
        summary=summary,
        region_results=region_results,
        decision_rule_version=DECISION_RULE_VERSION,
        embedding_model_version=EMBEDDING_MODEL_VERSION,
        reference_dataset_version=REFERENCE_DATASET_VERSION,
    )

    logger.info(
        "decision_made",
        decision_id=decision_id,
        scan_session_id=scan_session_id,
        result=decision_result,
    )

    return decision
