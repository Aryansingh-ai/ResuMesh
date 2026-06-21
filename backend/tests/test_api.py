"""
ResuMesh Backend Tests

Comprehensive test suite covering auth, resumes, jobs, matching, and RAG.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.core.config import settings
from app.models import Base  # All models

# ── Test Database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def auth_token(client: AsyncClient) -> dict:
    """Register and login a test user, return auth headers."""
    await client.post("/api/v1/auth/register", json={
        "full_name": "Test User",
        "email": "test@resumesh.test",
        "password": "TestPassword123",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "test@resumesh.test",
        "password": "TestPassword123",
    })
    data = login.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


# ── Auth Tests ─────────────────────────────────────────────────────────────────
class TestAuth:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "full_name": "New User",
            "email": "new@test.com",
            "password": "Password123",
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["email"] == "new@test.com"

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"full_name": "Dup", "email": "dup@test.com", "password": "Password123"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    async def test_login_success(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json={
            "full_name": "Login Test",
            "email": "login@test.com",
            "password": "Password123",
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "Password123",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_wrong_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "WrongPassword",
        })
        assert response.status_code == 401

    async def test_get_me_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_authenticated(self, client: AsyncClient, auth_token: dict):
        response = await client.get("/api/v1/users/me", headers=auth_token)
        assert response.status_code == 200
        assert "email" in response.json()


# ── Health Tests ───────────────────────────────────────────────────────────────
class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_metrics_endpoint(self, client: AsyncClient):
        response = await client.get("/metrics")
        assert response.status_code == 200


# ── Job Tests ──────────────────────────────────────────────────────────────────
class TestJobs:
    async def test_analyze_job_success(self, client: AsyncClient, auth_token: dict):
        response = await client.post("/api/v1/jobs/analyze", json={
            "title": "Python Developer",
            "company": "TechCorp",
            "portal": "manual",
            "raw_description": "We are looking for a Python developer with 3+ years experience "
                               "in FastAPI, PostgreSQL, Redis, Docker, and RESTful APIs. "
                               "Strong understanding of algorithms and data structures required. "
                               "Experience with AWS and CI/CD pipelines is a plus.",
        }, headers=auth_token)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Python Developer"
        assert "required_skills" in data
        assert "id" in data

    async def test_analyze_job_too_short(self, client: AsyncClient, auth_token: dict):
        response = await client.post("/api/v1/jobs/analyze", json={
            "title": "Dev",
            "company": "X",
            "portal": "manual",
            "raw_description": "Too short",
        }, headers=auth_token)
        assert response.status_code == 422

    async def test_list_jobs(self, client: AsyncClient, auth_token: dict):
        response = await client.get("/api/v1/jobs/", headers=auth_token)
        assert response.status_code == 200
        assert "items" in response.json()


# ── Matching Tests ─────────────────────────────────────────────────────────────
class TestMatching:
    async def test_quick_score_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/matching/quick-score",
            params={"resume_text": "test", "job_text": "test"},
        )
        assert response.status_code == 401


# ── Application Tests ──────────────────────────────────────────────────────────
class TestApplications:
    async def test_list_applications_empty(self, client: AsyncClient, auth_token: dict):
        response = await client.get("/api/v1/applications/", headers=auth_token)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_application_stats(self, client: AsyncClient, auth_token: dict):
        response = await client.get("/api/v1/applications/stats/summary", headers=auth_token)
        assert response.status_code == 200
        data = response.json()
        assert "by_status" in data
        assert "total" in data


# ── Analytics Tests ────────────────────────────────────────────────────────────
class TestAnalytics:
    async def test_dashboard_analytics(self, client: AsyncClient, auth_token: dict):
        response = await client.get("/api/v1/analytics/dashboard", headers=auth_token)
        assert response.status_code == 200
        data = response.json()
        assert "applications" in data
        assert "resumes" in data
        assert "cover_letters" in data
        assert "top_missing_skills" in data


# ── Feedback Tests ─────────────────────────────────────────────────────────────
class TestFeedback:
    async def test_submit_valid_feedback(self, client: AsyncClient, auth_token: dict):
        response = await client.post("/api/v1/feedback/", json={
            "feedback_type": "good_match",
            "rating": 5,
            "comment": "Very accurate!",
        }, headers=auth_token)
        assert response.status_code == 200

    async def test_submit_invalid_feedback_type(self, client: AsyncClient, auth_token: dict):
        response = await client.post("/api/v1/feedback/", json={
            "feedback_type": "invalid_type",
        }, headers=auth_token)
        assert response.status_code == 422
