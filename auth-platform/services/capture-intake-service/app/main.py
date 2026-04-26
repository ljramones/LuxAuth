import sys

sys.path.insert(0, "/app/libs/auth_common")

from auth_common.correlation import CorrelationMiddleware
from auth_common.logging import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.settings import settings

logger = get_logger(settings.service_name)
app = FastAPI(title=settings.service_name)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CorrelationMiddleware)
app.include_router(router)

@app.on_event("startup")
async def startup():
    logger.info("service_starting", port=settings.port)

@app.on_event("shutdown")
async def shutdown():
    logger.info("service_stopping")
