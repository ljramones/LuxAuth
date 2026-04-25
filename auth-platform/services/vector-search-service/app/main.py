import sys

sys.path.insert(0, "/app/libs/auth_common")

from fastapi import FastAPI

from auth_common.correlation import CorrelationMiddleware
from auth_common.logging import get_logger

from app.routes import router
from app.settings import settings

logger = get_logger(settings.service_name)

app = FastAPI(
    title="Vector Search Service",
    version="0.1.0",
    description="Performs similarity search against reference embeddings for authentication",
)

app.add_middleware(CorrelationMiddleware)
app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    logger.info(
        "vector-search-service starting",
        extra={"port": settings.port, "log_level": settings.log_level},
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("vector-search-service shutting down")
