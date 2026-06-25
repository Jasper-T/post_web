from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.app.api.router import api_router
from backend.app.core.config import CORS_ORIGINS
from backend.app.core.logging import configure_logging
from backend.app.core.middleware import RequestLoggingMiddleware
from backend.app.static.frontend import mount_frontend
from backend.app.services.visualization import clear_all_visualization_caches


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting title={}", app.title)
    clear_all_visualization_caches()
    try:
        yield
    finally:
        logger.info("Application stopping title={}", app.title)
        logger.complete()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Workspace File Browser", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(api_router)
    mount_frontend(app)
    return app
