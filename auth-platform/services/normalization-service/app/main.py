import asyncio
import sys

sys.path.insert(0, "/app/libs/auth_common")

from auth_common.correlation import CorrelationMiddleware
from auth_common.logging import get_logger
from auth_common.worker import run_worker
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.settings import settings
from app.worker import handle_message

logger = get_logger(settings.service_name)

app = FastAPI(
    title="Normalization Service",
    version="0.1.0",
    description="Normalizes evidence images for the luxury authentication pipeline",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CorrelationMiddleware)
app.include_router(router)

_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    global _worker_task
    logger.info("service_starting", port=settings.port)
    _worker_task = asyncio.create_task(
        run_worker(
            settings.consume_queue,
            handle_message,
            service_name=settings.service_name,
        )
    )


@app.on_event("shutdown")
async def shutdown():
    if _worker_task:
        _worker_task.cancel()
    logger.info("service_stopping")
