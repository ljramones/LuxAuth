import uuid
from datetime import UTC, datetime

from auth_common.database import get_db
from auth_common.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings

logger = get_logger(settings.service_name)
router = APIRouter()


class CreateReviewCaseRequest(BaseModel):
    scan_session_id: str
    authentication_decision_id: str


class ReviewDecisionRequest(BaseModel):
    reviewer_decision: str
    reviewer_notes: str
    reviewer_id: str


@router.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready", "service": settings.service_name}


@router.get("/review-cases")
async def list_review_cases(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM review_cases ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset},
    )
    rows = result.mappings().all()
    return {"review_cases": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.get("/review-cases/{review_case_id}")
async def get_review_case(review_case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM review_cases WHERE id = :id"),
        {"id": review_case_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Review case not found")
    return dict(row)


@router.post("/review-cases")
async def create_review_case(body: CreateReviewCaseRequest, db: AsyncSession = Depends(get_db)):
    review_case_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    await db.execute(
        text(
            """
            INSERT INTO review_cases (
                id, scan_session_id, authentication_decision_id,
                status, created_at
            ) VALUES (
                :id, :scan_session_id, :authentication_decision_id,
                'PENDING', :created_at
            )
            """
        ),
        {
            "id": review_case_id,
            "scan_session_id": body.scan_session_id,
            "authentication_decision_id": body.authentication_decision_id,
            "created_at": now,
        },
    )
    await db.commit()

    logger.info("review_case_created", review_case_id=review_case_id)
    return {
        "id": review_case_id,
        "scan_session_id": body.scan_session_id,
        "authentication_decision_id": body.authentication_decision_id,
        "status": "PENDING",
        "created_at": now.isoformat(),
    }


@router.post("/review-cases/{review_case_id}/decision")
async def submit_review_decision(
    review_case_id: str,
    body: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: audit trail for reviewer actions
    now = datetime.now(UTC)

    result = await db.execute(
        text("SELECT id FROM review_cases WHERE id = :id"),
        {"id": review_case_id},
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Review case not found")

    await db.execute(
        text(
            """
            UPDATE review_cases SET
                reviewer_decision = :reviewer_decision,
                reviewer_notes = :reviewer_notes,
                reviewer_id = :reviewer_id,
                status = 'COMPLETED',
                updated_at = :updated_at
            WHERE id = :id
            """
        ),
        {
            "id": review_case_id,
            "reviewer_decision": body.reviewer_decision,
            "reviewer_notes": body.reviewer_notes,
            "reviewer_id": body.reviewer_id,
            "updated_at": now,
        },
    )
    await db.commit()

    logger.info(
        "review_decision_submitted",
        review_case_id=review_case_id,
        reviewer_decision=body.reviewer_decision,
    )
    return {
        "id": review_case_id,
        "reviewer_decision": body.reviewer_decision,
        "status": "COMPLETED",
        "updated_at": now.isoformat(),
    }
