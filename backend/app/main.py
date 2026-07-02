"""
ResuMesh FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from loguru import logger
import time

from app.core.config import settings
from app.core.database import init_db, close_db, get_db
from app.core.logging_config import setup_logging
from app.core.metrics import setup_metrics
from app.api.v1.router import api_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — startup and shutdown."""
    # Startup
    setup_logging()
    logger.bind(version=settings.APP_VERSION, env=settings.APP_ENV).info("Starting ResuMesh API")

    await init_db()
    logger.info("Database initialized")

    try:
        from app.services.supabase_storage import get_storage_service
        await get_storage_service().initialize_bucket("resumes")
    except Exception as e:
        logger.bind(error=str(e).warning("Failed to initialize Supabase storage bucket during startup."))

    try:
        from app.services.embedding_service import get_embedding_service
        await get_embedding_service().initialize()
        logger.info("Embedding service initialized")
    except Exception as e:
        logger.bind(error=str(e).warning("Failed to initialize embedding service during startup. App will run in degraded mode."))

    logger.bind(host=settings.BACKEND_HOST, port=settings.BACKEND_PORT).info("ResuMesh API ready")
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

    # ── Metrics Setup (must run before application starts) ──────────────────
    setup_metrics(app)

    # ── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Exception Handlers ──────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.bind(path=str(request.url).error("Unhandled exception"),
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
    async def health_check(db: AsyncSession = Depends(get_db)):
        database_status = "connected"
        overall_status = "healthy"
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            logger.bind(error=str(e).error("Database health check failed"))
            database_status = "disconnected"
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "database": database_status,
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
