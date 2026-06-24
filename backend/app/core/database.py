"""
Database configuration using SQLAlchemy async engine.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://") and "asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

is_sqlite = db_url.startswith("sqlite")

engine_kwargs = {
    "echo": settings.DEBUG,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })

engine: AsyncEngine = create_async_engine(
    db_url,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base Model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Lifecycle ─────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Initialize database — create all tables if they don't exist."""
    from app.models import (  # noqa: F401 — import to register models
        user, resume, job, application, cover_letter,
    )

    async with engine.begin() as conn:
        if not is_sqlite:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def close_db() -> None:
    """Close all database connections."""
    await engine.dispose()
    logger.info("Database connections closed")


# ── Dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
