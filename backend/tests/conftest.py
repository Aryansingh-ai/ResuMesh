"""
Pytest configuration and global fixtures.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

# Set environment variables BEFORE importing app configuration
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost:5432/test"
os.environ["SUPABASE_URL"] = "http://localhost:8000"
os.environ["SUPABASE_ANON_KEY"] = "test_key"
os.environ["JWT_SECRET_KEY"] = "test_secret"

from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.postgres_models import User
import uuid
from datetime import datetime, timezone

# -----------------------------------------------------------------------------
# Test User Fixture
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        full_name="Test User",
        role="user",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc)
    )


# -----------------------------------------------------------------------------
# Database Session Mock
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_db_session():
    """Mock the AsyncSession for database operations."""
    session = AsyncMock()
    
    # Mocking a basic execute().scalar_one_or_none()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    
    session.execute.return_value = mock_result
    return session


# -----------------------------------------------------------------------------
# FastAPI Dependency Overrides
# -----------------------------------------------------------------------------
@pytest.fixture
def override_get_db(mock_db_session):
    async def _get_db():
        yield mock_db_session
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def override_get_current_user(mock_user):
    async def _get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = _get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# -----------------------------------------------------------------------------
# Async HTTP Client for API tests
# -----------------------------------------------------------------------------
@pytest.fixture
async def async_client(override_get_db, override_get_current_user):
    """Provides an async client to test FastAPI endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
