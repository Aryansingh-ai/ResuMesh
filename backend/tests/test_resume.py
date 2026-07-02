import pytest
from unittest.mock import patch, AsyncMock
from app.models.postgres_models import Resume
import uuid

@pytest.fixture
def mock_storage_service():
    with patch("app.api.v1.endpoints.resumes.get_storage_service") as mock_get:
        service = AsyncMock()
        mock_get.return_value = service
        yield service

@pytest.mark.asyncio
async def test_upload_resume_success(async_client, mock_db_session, mock_storage_service):
    # Mock file hash check
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    
    files = {"file": ("test_resume.pdf", b"dummy pdf content", "application/pdf")}
    data = {"title": "My Resume"}

    with patch("app.api.v1.endpoints.resumes.BackgroundTasks.add_task") as mock_bg:
        response = await async_client.post("/api/v1/resumes/upload", files=files, data=data)
        
        assert response.status_code == 201
        assert response.json()["title"] == "My Resume"
        assert response.json()["file_type"] == "pdf"
        mock_storage_service.upload_file.assert_called_once()
        mock_bg.assert_called_once()

@pytest.mark.asyncio
async def test_upload_invalid_extension(async_client):
    files = {"file": ("test.txt", b"text content", "text/plain")}
    data = {"title": "Invalid Resume"}
    
    response = await async_client.post("/api/v1/resumes/upload", files=files, data=data)
    
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_resumes(async_client, mock_db_session):
    mock_resume = Resume(
        id=uuid.uuid4(),
        title="Software Engineer Resume",
        file_name="resume.pdf",
        file_type="pdf",
        is_primary=True,
        is_parsed=True
    )
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_resume]
    
    response = await async_client.get("/api/v1/resumes/")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Software Engineer Resume"

@pytest.mark.asyncio
async def test_get_resume_not_found(async_client, mock_db_session):
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
    response = await async_client.get(f"/api/v1/resumes/{uuid.uuid4()}")
    assert response.status_code == 404
