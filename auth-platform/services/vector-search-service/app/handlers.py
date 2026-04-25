import hashlib
import sys
from uuid import UUID

sys.path.insert(0, "/app/libs/auth_common")

from sqlalchemy.ext.asyncio import AsyncSession

from auth_common.events import EventEnvelope, EventTypes
from auth_common.logging import get_logger
from auth_common.messaging import send_message
from auth_common.models import VectorSearchResult

from app.settings import settings

logger = get_logger(settings.service_name)


async def search_similar(
    image_asset_id: UUID, db_session: AsyncSession
) -> VectorSearchResult:
    """Find the most similar reference embeddings for a given image.

    Currently a deterministic stub that generates fake similarity scores
    derived from the image_asset_id.  When reference embedding seeding and
    schema links are finalised, this will be replaced with a real pgvector
    nearest-neighbour query using the cosine distance operator (<=>>).
    """

    # Deterministic seed from image_asset_id
    seed = (
        int(hashlib.sha256(str(image_asset_id).encode()).hexdigest(), 16) % 1000
    )

    authentic_sim = 0.75 + (seed % 25) / 100.0
    counterfeit_sim = 0.30 + (seed % 20) / 100.0
    ood_score = 1.0 - authentic_sim

    nearest_authentic = [
        {"reference_id": f"ref-{str(i).zfill(3)}", "similarity": round(authentic_sim - i * 0.02, 4)}
        for i in range(settings.top_k)
    ]
    nearest_counterfeit = [
        {"reference_id": f"ref-9{str(i).zfill(2)}", "similarity": round(counterfeit_sim - i * 0.01, 4)}
        for i in range(settings.top_k)
    ]

    authentic_cluster_score = sum(
        m["similarity"] for m in nearest_authentic
    ) / len(nearest_authentic)
    counterfeit_cluster_score = sum(
        m["similarity"] for m in nearest_counterfeit
    ) / len(nearest_counterfeit)

    result = VectorSearchResult(
        image_asset_id=image_asset_id,
        nearest_authentic=nearest_authentic,
        nearest_counterfeit=nearest_counterfeit,
        authentic_cluster_score=round(authentic_cluster_score, 4),
        counterfeit_cluster_score=round(counterfeit_cluster_score, 4),
        ood_score=round(ood_score, 4),
    )

    # Publish downstream
    envelope = EventEnvelope(
        event_type=EventTypes.VECTOR_SEARCH_COMPLETED,
        payload={
            "image_asset_id": str(image_asset_id),
            "authentic_cluster_score": result.authentic_cluster_score,
            "counterfeit_cluster_score": result.counterfeit_cluster_score,
            "ood_score": result.ood_score,
        },
    )
    send_message(settings.sqs_region_scoring_queue, envelope)
    logger.info(
        "vector search complete - published to region-scoring queue",
        extra={"image_asset_id": str(image_asset_id)},
    )

    # TODO: implement real pgvector nearest-neighbour search against reference embeddings
    # TODO: emit audit event

    return result
