"""
ResuMesh FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging_config import setup_logging
from app.core.metrics import setup_metrics
from app.api.v1.router import api_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — startup and shutdown."""
    # Startup
    setup_logging()
    logger.info("Starting ResuMesh API", version=settings.APP_VERSION, env=settings.APP_ENV)

    await init_db()
    logger.info("Database initialized")

    setup_metrics(app)
    logger.info("Metrics configured")

    logger.info("ResuMesh API ready", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT)
    yield

    # Shutdown
    await close_db()
    logger.info("ResuMesh API shut down cleanly")


def create_application() -> FastAPI:
    """Factory function to create the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered Job Application Copilot — REST API",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Middleware ──────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"],  # Restrict in production
    )

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggerMiddleware)

    # ── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Exception Handlers ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An internal server error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )

    # ── Health Endpoints ────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "env": settings.APP_ENV,
        }

    @app.get("/ready", tags=["System"])
    async def readiness_check():
        """Kubernetes/Docker readiness probe."""
        return {"status": "ready"}

    return app


app = create_application()
