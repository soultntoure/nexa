"""
FastAPI app factory + lifespan.

Creates the app, mounts the /api router, registers middleware.
"""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.config import get_settings
from app.data.db.engine import AsyncSessionLocal
from app.services.chat import init_analyst_agent, warmup_analyst_agent
from app.services.control.feedback_loop_service import FeedbackLoopService
from app.services.prefraud.detection_scheduler import start_detection_scheduler
from app.services.prefraud.detection_service import PatternDetectionService
from app.services.prefraud.posture_scheduler import start_posture_scheduler
from app.services.prefraud.posture_service import PostureService

logger = logging.getLogger(__name__)
settings = get_settings()
SYNC_DB_URI = settings.POSTGRES_URL.replace("+asyncpg", "").split("?")[0]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle."""
    app.state.feedback_loop_service = FeedbackLoopService(AsyncSessionLocal)
    app.state.posture_service = PostureService(AsyncSessionLocal)
    app.state.posture_scheduler_task = start_posture_scheduler(
        app.state.posture_service,
    )
    app.state.detection_service = PatternDetectionService(AsyncSessionLocal)
    app.state.detection_scheduler_task = start_detection_scheduler(
        app.state.detection_service,
    )
    logger.info("FeedbackLoopService + PostureService + DetectionService initialized")

    init_analyst_agent()
    await warmup_analyst_agent()

    if settings.BACKGROUND_AUDIT_ENABLED:
        from app.services.background_audit.facade import BackgroundAuditFacade
        app.state.background_audit_facade = BackgroundAuditFacade(AsyncSessionLocal)
        logger.info("BackgroundAuditFacade initialized")

    logger.info("Docs available at http://localhost:8080/docs")
    yield
    if hasattr(app.state, "posture_scheduler_task"):
        app.state.posture_scheduler_task.cancel()
    if hasattr(app.state, "detection_scheduler_task"):
        app.state.detection_scheduler_task.cancel()
    if hasattr(app.state, "posture_service"):
        del app.state.posture_service
    logger.info("Shutting down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Fraud Detection API",
        description="AI-powered payment fraud detection with composite signal analysis",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        root_path="",
    )


    app.include_router(api_router)

    static_dir = Path(__file__).resolve().parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/static/test.html")

    return app


app = create_app()
