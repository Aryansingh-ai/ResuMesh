import pytest
from unittest.mock import patch, AsyncMock
from app.models.postgres_models import Resume, ParsedResume, Job, JobDescription
import uuid

@pytest.mark.asyncio
async def test_generate_cover_letter(async_client, mock_db_session):
    mock_resume = Resume(id=uuid.uuid4(), user_id=uuid.uuid4())
    mock_parsed = ParsedResume(full_name="Jane Doe", skills={"python": 5}, experience=[])
    mock_job = Job(id=uuid.uuid4(), title="Python Dev", company="Tech Corp")
    mock_job_desc = JobDescription(required_skills=["python"])
    
    mock_scalar = mock_db_session.execute.return_value.scalar_one_or_none
    mock_scalar.side_effect = [mock_resume, mock_parsed, mock_job, mock_job_desc, None]
    
    with patch("app.api.v1.endpoints.cover_letters.CoverLetterGenerator.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Dear Hiring Manager, I am a great fit for the Python Dev role at Tech Corp."
        
        response = await async_client.post(
            "/api/v1/coverletters/generate",
            json={
                "resume_id": str(mock_resume.id),
                "job_id": str(mock_job.id),
                "tone": "professional",
                "save": False
            }
        )
        
        assert response.status_code == 200
        assert "Dear Hiring Manager" in response.json()["content"]
        assert response.json()["word_count"] > 5

@pytest.mark.asyncio
async def test_generate_cover_letter_missing_resume(async_client, mock_db_session):
    mock_scalar = mock_db_session.execute.return_value.scalar_one_or_none
    mock_scalar.side_effect = [None]
    
    response = await async_client.post(
        "/api/v1/coverletters/generate",
        json={"resume_id": str(uuid.uuid4()), "job_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404
