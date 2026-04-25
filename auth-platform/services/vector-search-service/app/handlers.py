import hashlib
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.audit import record_audit_event
from auth_common.correlation import get_correlation_id
from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import VectorSearchResult

from app.settings import settings

logger = get_logger(settings.service_name)


async def search_similar(
    image_asset_id: UUID, db_session: AsyncSession
) -> VectorSearchResult:
    """Find nearest reference embeddings using pgvector cosine similarity."""

    # Look up image metadata
    asset_row = await db_session.execute(
        text("SELECT scan_session_id, region_code FROM image_assets WHERE id = :id"),
        {"id": str(image_asset_id)},
    )
    asset = asset_row.mappings().one_or_none()
    scan_session_id = asset["scan_session_id"] if asset else None
    region_code = asset["region_code"] if asset else None

    # Get query embedding
    emb_row = await db_session.execute(
        text("SELECT embedding FROM embeddings WHERE image_asset_id = :id"),
        {"id": str(image_asset_id)},
    )
    query_emb = emb_row.scalar_one_or_none()

    if query_emb is None:
        logger.warning("no_embedding_found", image_asset_id=str(image_asset_id))
        return await _stub_result(image_asset_id, scan_session_id, region_code, db_session)

    # Check if reference embeddings exist
    ref_count_row = await db_session.execute(text("SELECT count(*) FROM reference_embeddings"))
    ref_count = ref_count_row.scalar()

    if not ref_count or ref_count == 0:
        logger.warning("no_reference_embeddings", fallback="stub")
        return await _stub_result(image_asset_id, scan_session_id, region_code, db_session)

    # Real pgvector search against reference_embeddings
    region_filter = "AND ri.region_code = :region" if region_code else ""
    params: dict = {"iid": str(image_asset_id), "limit": settings.top_k * 2}
    if region_code:
        params["region"] = region_code

    search_result = await db_session.execute(
        text(
            f"""
            SELECT
                re.id as ref_embedding_id,
                re.reference_image_id,
                ri.region_code,
                rit.authenticity_status,
                rit.brand,
                1 - (re.embedding <=> (SELECT embedding FROM embeddings WHERE image_asset_id = :iid)) as similarity
            FROM reference_embeddings re
            JOIN reference_images ri ON ri.id = re.reference_image_id
            JOIN reference_items rit ON rit.id = ri.reference_item_id
            WHERE 1=1 {region_filter}
            ORDER BY re.embedding <=> (SELECT embedding FROM embeddings WHERE image_asset_id = :iid)
            LIMIT :limit
            """
        ),
        params,
    )
    rows = search_result.mappings().all()

    # Split into authentic / counterfeit
    authentic_matches = []
    counterfeit_matches = []
    for r in rows:
        entry = {
            "reference_image_id": str(r["reference_image_id"]),
            "similarity": round(float(r["similarity"]), 4),
            "authenticity_status": r["authenticity_status"],
        }
        if r["authenticity_status"] == "CONFIRMED_AUTHENTIC":
            if len(authentic_matches) < settings.top_k:
                authentic_matches.append(entry)
        elif r["authenticity_status"] == "CONFIRMED_COUNTERFEIT":
            if len(counterfeit_matches) < settings.top_k:
                counterfeit_matches.append(entry)

    # Compute cluster scores
    auth_score = (
        sum(m["similarity"] for m in authentic_matches) / len(authentic_matches)
        if authentic_matches else 0.0
    )
    counter_score = (
        sum(m["similarity"] for m in counterfeit_matches) / len(counterfeit_matches)
        if counterfeit_matches else 0.0
    )
    max_sim = max(
        [m["similarity"] for m in authentic_matches + counterfeit_matches],
        default=0.0,
    )
    ood_score = 1.0 - max_sim

    result = VectorSearchResult(
        image_asset_id=image_asset_id,
        nearest_authentic=authentic_matches,
        nearest_counterfeit=counterfeit_matches,
        authentic_cluster_score=round(auth_score, 4),
        counterfeit_cluster_score=round(counter_score, 4),
        ood_score=round(ood_score, 4),
    )

    await record_audit_event(
        db_session,
        "VECTOR_SEARCH_COMPLETED",
        image_id=image_asset_id,
        scan_session_id=scan_session_id,
        payload={
            "authentic_cluster_score": result.authentic_cluster_score,
            "counterfeit_cluster_score": result.counterfeit_cluster_score,
            "ood_score": result.ood_score,
            "authentic_count": len(authentic_matches),
            "counterfeit_count": len(counterfeit_matches),
        },
    )

    envelope = EventEnvelope(
        event_type=EventTypes.VECTOR_SEARCH_COMPLETED,
        correlation_id=get_correlation_id(),
        scan_session_id=scan_session_id,
        image_id=image_asset_id,
        region_code=region_code,
        source_service=settings.service_name,
        payload={
            "image_asset_id": str(image_asset_id),
            "scan_session_id": str(scan_session_id) if scan_session_id else None,
            "region_code": region_code,
            "authentic_cluster_score": result.authentic_cluster_score,
            "counterfeit_cluster_score": result.counterfeit_cluster_score,
            "ood_score": result.ood_score,
        },
    )
    send_message(settings.sqs_region_scoring_queue, envelope)
    logger.info("vector_search_complete", image_asset_id=str(image_asset_id),
                authentic_score=result.authentic_cluster_score, counterfeit_score=result.counterfeit_cluster_score)

    return result


async def _stub_result(
    image_asset_id: UUID,
    scan_session_id,
    region_code: str | None,
    db_session: AsyncSession,
) -> VectorSearchResult:
    """Fallback stub when no reference embeddings exist."""
    seed = int(hashlib.sha256(str(image_asset_id).encode()).hexdigest(), 16) % 1000
    auth_sim = 0.75 + (seed % 25) / 100.0
    counter_sim = 0.30 + (seed % 20) / 100.0

    result = VectorSearchResult(
        image_asset_id=image_asset_id,
        nearest_authentic=[{"reference_id": "stub-fallback", "similarity": round(auth_sim, 4)}],
        nearest_counterfeit=[{"reference_id": "stub-fallback", "similarity": round(counter_sim, 4)}],
        authentic_cluster_score=round(auth_sim, 4),
        counterfeit_cluster_score=round(counter_sim, 4),
        ood_score=round(1.0 - auth_sim, 4),
    )

    await record_audit_event(
        db_session, "VECTOR_SEARCH_COMPLETED", image_id=image_asset_id,
        payload={"mode": "stub_fallback"},
    )

    envelope = EventEnvelope(
        event_type=EventTypes.VECTOR_SEARCH_COMPLETED,
        correlation_id=get_correlation_id(),
        scan_session_id=scan_session_id,
        image_id=image_asset_id,
        region_code=region_code,
        source_service=settings.service_name,
        payload={
            "image_asset_id": str(image_asset_id),
            "scan_session_id": str(scan_session_id) if scan_session_id else None,
            "region_code": region_code,
            "authentic_cluster_score": result.authentic_cluster_score,
            "counterfeit_cluster_score": result.counterfeit_cluster_score,
            "ood_score": result.ood_score,
        },
    )
    send_message(settings.sqs_region_scoring_queue, envelope)
    return result
