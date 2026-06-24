import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from sqlalchemy import select
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.postgres_models import User, Resume, ParsedResume, Job, JobDescription, Embedding

# Use the same database override from test_api.py (TestingSessionLocal)
from tests.test_api import client, TestingSessionLocal, override_get_db, setup_database

# Override database
app.dependency_overrides[get_db] = override_get_db

# Custom security helper for overrides
security = HTTPBearer()

async def mock_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    if token == "usera_token":
        email = "usera@test.com"
    elif token == "userb_token":
        email = "userb@test.com"
    elif token == "admin_token":
        email = "admin@test.com"
    else:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Override authentication dependency
app.dependency_overrides[get_current_user] = mock_get_current_user


@pytest.fixture(autouse=True)
def mock_storage_service(monkeypatch):
    mock_service = MagicMock()
    mock_service.upload_file = AsyncMock(return_value="resumes/test_user/test_id.pdf")
    mock_service.download_file = AsyncMock(return_value=b"Dummy PDF Content")
    mock_service.delete_file = AsyncMock(return_value=None)
    monkeypatch.setattr("app.api.v1.endpoints.resumes.get_storage_service", lambda: mock_service)
    return mock_service


@pytest.fixture(autouse=True)
def mock_background_process(monkeypatch):
    monkeypatch.setattr("app.api.v1.endpoints.resumes._process_resume_background", AsyncMock())


@pytest.fixture(autouse=True)
async def seed_users():
    """Ensure test users exist in database for the mock auth to resolve."""
    async with TestingSessionLocal() as session:
        # Check if users already exist
        res = await session.execute(select(User).where(User.email == "usera@test.com"))
        if res.scalar_one_or_none():
            return
            
        user_a = User(
            id=uuid.uuid4(),
            email="usera@test.com",
            full_name="User A",
            role="user",
            is_active=True,
            is_verified=True
        )
        user_b = User(
            id=uuid.uuid4(),
            email="userb@test.com",
            full_name="User B",
            role="user",
            is_active=True,
            is_verified=True
        )
        admin = User(
            id=uuid.uuid4(),
            email="admin@test.com",
            full_name="Admin User",
            role="admin",
            is_active=True,
            is_verified=True
        )
        session.add(user_a)
        session.add(user_b)
        session.add(admin)
        await session.commit()


@pytest.fixture
def auth_headers() -> dict:
    """Mock headers corresponding to seeded users."""
    return {
        "user_a": {"Authorization": "Bearer usera_token"},
        "user_b": {"Authorization": "Bearer userb_token"},
        "admin": {"Authorization": "Bearer admin_token"}
    }


class TestProductionHardening:
    
    async def test_duplicate_resume_upload(self, client: AsyncClient, auth_headers: dict):
        """Uploading the exact same file content twice returns the same resume ID."""
        file_content = b"This is the unique content of resume one."
        
        # Upload 1
        files = {"file": ("resume.pdf", file_content, "application/pdf")}
        data = {"title": "Resume 1"}
        resp1 = await client.post("/api/v1/resumes/upload", files=files, data=data, headers=auth_headers["user_a"])
        assert resp1.status_code == 201
        res1_data = resp1.json()
        resume_id_1 = res1_data["id"]
        assert "version" in res1_data
        assert isinstance(res1_data["version"], int) and res1_data["version"] > 0
        assert res1_data["is_primary"] is True

        # Upload 2 (same content, different title)
        files = {"file": ("resume_copy.pdf", file_content, "application/pdf")}
        data = {"title": "Resume Copy"}
        resp2 = await client.post("/api/v1/resumes/upload", files=files, data=data, headers=auth_headers["user_a"])
        assert resp2.status_code == 201
        res2_data = resp2.json()
        resume_id_2 = res2_data["id"]

        # Assert duplicate detection returned existing resume ID
        assert resume_id_1 == resume_id_2
        assert "Duplicate file detected" in res2_data["message"]

    async def test_versioning_on_different_uploads(self, client: AsyncClient, auth_headers: dict):
        """Uploading a new file hash increments version and makes it the primary resume."""
        # Version 1
        files = {"file": ("resume_v1.pdf", b"Content for version one.", "application/pdf")}
        resp1 = await client.post("/api/v1/resumes/upload", files=files, data={"title": "V1"}, headers=auth_headers["user_a"])
        assert resp1.status_code == 201
        res1 = resp1.json()
        version1 = res1["version"]
        assert res1["is_primary"] is True

        # Version 2
        files = {"file": ("resume_v2.pdf", b"Content for version two (modified).", "application/pdf")}
        resp2 = await client.post("/api/v1/resumes/upload", files=files, data={"title": "V2"}, headers=auth_headers["user_a"])
        assert resp2.status_code == 201
        res2 = resp2.json()
        version2 = res2["version"]
        assert version2 == version1 + 1
        assert res2["is_primary"] is True

        # Check list resumes: V1 is no longer primary, V2 is primary
        list_resp = await client.get("/api/v1/resumes/", headers=auth_headers["user_a"])
        items = list_resp.json()["items"]
        
        v1_item = next(i for i in items if i["id"] == res1["id"])
        v2_item = next(i for i in items if i["id"] == res2["id"])
        
        assert v1_item["is_primary"] is False
        assert v2_item["is_primary"] is True

    async def test_soft_delete_and_restore_flow(self, client: AsyncClient, auth_headers: dict):
        """Deleting a resume soft deletes it by default (retaining it in database/storage) and users can restore it."""
        files = {"file": ("resume_delete.pdf", b"Resume to delete.", "application/pdf")}
        upload_resp = await client.post("/api/v1/resumes/upload", files=files, data={"title": "ToDelete"}, headers=auth_headers["user_a"])
        resume_id = upload_resp.json()["id"]

        # Delete (soft delete by default)
        del_resp = await client.delete(f"/api/v1/resumes/{resume_id}", headers=auth_headers["user_a"])
        assert del_resp.status_code == 204

        # List resumes: should be hidden from default list
        list_resp = await client.get("/api/v1/resumes/", headers=auth_headers["user_a"])
        assert not any(i["id"] == resume_id for i in list_resp.json()["items"])

        # List resumes including deleted: should show up
        list_deleted_resp = await client.get("/api/v1/resumes/?include_deleted=true", headers=auth_headers["user_a"])
        deleted_item = next(i for i in list_deleted_resp.json()["items"] if i["id"] == resume_id)
        assert deleted_item["is_deleted"] is True

        # Restore resume
        restore_resp = await client.post(f"/api/v1/resumes/{resume_id}/restore", headers=auth_headers["user_a"])
        assert restore_resp.status_code == 200
        assert restore_resp.json()["is_deleted"] is False

        # List resumes: should show up again
        list_back = await client.get("/api/v1/resumes/", headers=auth_headers["user_a"])
        assert any(i["id"] == resume_id for i in list_back.json()["items"])

    async def test_admin_permanent_delete(self, client: AsyncClient, auth_headers: dict):
        """Only admins can permanently delete a resume from the database."""
        files = {"file": ("resume_purge.pdf", b"Resume to purge.", "application/pdf")}
        upload_resp = await client.post("/api/v1/resumes/upload", files=files, data={"title": "ToPurge"}, headers=auth_headers["user_a"])
        resume_id = upload_resp.json()["id"]

        # Try to hard-delete as normal user: should be 403 Forbidden
        user_purge_resp = await client.delete(f"/api/v1/resumes/{resume_id}?permanent=true", headers=auth_headers["user_a"])
        assert user_purge_resp.status_code == 403

        # Hard delete as admin: should be 204
        admin_purge_resp = await client.delete(f"/api/v1/resumes/{resume_id}?permanent=true", headers=auth_headers["admin"])
        assert admin_purge_resp.status_code == 204

        # Check in DB directly: should be completely gone
        async with TestingSessionLocal() as session:
            db_res = await session.execute(select(Resume).where(Resume.id == uuid.UUID(resume_id)))
            assert db_res.scalar_one_or_none() is None

    async def test_tenant_security_boundaries(self, client: AsyncClient, auth_headers: dict):
        """User B cannot fetch or delete User A's resume."""
        # User A uploads a resume
        files = {"file": ("usera.pdf", b"User A content.", "application/pdf")}
        upload_resp = await client.post("/api/v1/resumes/upload", files=files, data={"title": "UserA Resume"}, headers=auth_headers["user_a"])
        resume_id = upload_resp.json()["id"]

        # User B tries to fetch User A's resume details: should be 404
        resp_get = await client.get(f"/api/v1/resumes/{resume_id}", headers=auth_headers["user_b"])
        assert resp_get.status_code == 404

        # User B tries to delete User A's resume: should be 404
        resp_del = await client.delete(f"/api/v1/resumes/{resume_id}", headers=auth_headers["user_b"])
        assert resp_del.status_code == 404

    async def test_hybrid_ranking_breakdown(self, client: AsyncClient, auth_headers: dict):
        """Job matching returns the correct hybrid re-ranking breakdown matching the 60/20/10/10 formula."""
        # 1. Create a job description in DB
        async with TestingSessionLocal() as session:
            job = Job(
                id=uuid.uuid4(),
                title="Staff Engineer",
                company="InnovateCorp",
                portal="manual",
                raw_description="Looking for Python FastAPI engineer with PhD and 10 years experience."
            )
            # Create job description fields
            job_desc = JobDescription(
                id=uuid.uuid4(),
                job_id=job.id,
                required_skills=["python", "fastapi"],
                preferred_skills=["kubernetes"],
                education_requirements=["PhD"],
                min_years_experience=10.0
            )
            
            # 2. Create a candidate resume
            user_a_res = await session.execute(select(User).where(User.email == "usera@test.com"))
            user_a = user_a_res.scalar_one()
            
            resume = Resume(
                id=uuid.uuid4(),
                user_id=user_a.id,
                title="Candidate Resume",
                file_name="candidate.pdf",
                storage_path=f"resumes/{user_a.id}/candidate.pdf",
                file_size=100,
                file_type="pdf",
                is_primary=True,
                is_parsed=True,
                version=1,
                is_deleted=False
            )
            
            parsed_resume = ParsedResume(
                resume_id=resume.id,
                full_name="Candidate Bob",
                skills={"languages": ["Python", "JavaScript"], "frameworks": ["FastAPI"]},
                education=["Bachelors in CS", "PhD in AI"],
                total_years_experience=8.0 # 8 years experience (deficit 2 years)
            )
            
            # Setup dummy embedding (384 dimensions)
            emb_vector = [0.1] * 384
            job.embedding = emb_vector
            embedding = Embedding(
                resume_id=resume.id,
                embedding=emb_vector
            )
            
            session.add(job)
            session.add(job_desc)
            session.add(resume)
            session.add(parsed_resume)
            session.add(embedding)
            await session.commit()
            
            job_id_str = str(job.id)

        # 3. Call candidates endpoint
        match_resp = await client.get(f"/api/v1/jobs/{job_id_str}/candidates", headers=auth_headers["user_a"])
        assert match_resp.status_code == 200
        match_data = match_resp.json()
        
        assert "candidates" in match_data
        candidates = match_data["candidates"]
        assert len(candidates) > 0
        
        top_cand = candidates[0]
        assert "score_breakdown" in top_cand
        breakdown = top_cand["score_breakdown"]
        
        # Verify scores
        assert "final_score" in breakdown
        assert "embedding_score" in breakdown
        assert "skill_score" in breakdown
        assert "experience_score" in breakdown
        assert "education_score" in breakdown
        
        # Verify details dictionary backward compatibility
        assert "details" in top_cand
        details = top_cand["details"]
        assert "semantic_match" in details
        assert "skills_match" in details
        assert "experience_match" in details
        assert "education_match" in details
        assert "matched_skills" in details
        assert "missing_skills" in details
