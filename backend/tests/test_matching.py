import pytest
from unittest.mock import patch, AsyncMock
from app.models.postgres_models import Resume, ParsedResume, Job, JobDescription
import uuid

@pytest.mark.asyncio
async def test_compute_match_score(async_client, mock_db_session):
    # Setup mocks for db fetching
    mock_resume = Resume(id=uuid.uuid4(), user_id=uuid.uuid4())
    mock_parsed = ParsedResume(full_name="John Doe", skills={"python": 5}, experience=[])
    mock_job = Job(id=uuid.uuid4(), title="Python Dev", raw_description="Need python")
    
    # We use a custom side_effect to return different models on sequential scalar_one_or_none calls
    mock_scalar = mock_db_session.execute.return_value.scalar_one_or_none
    mock_scalar.side_effect = [mock_resume, mock_parsed, mock_job, None, None]

    with patch("app.api.v1.endpoints.matching.MatchingEngine.match", new_callable=AsyncMock) as mock_match:
        from app.services.matching_engine import MatchResult
        mock_match.return_value = MatchResult(
            score=85.0,
            matched_skills=["python"],
            missing_skills=[],
            recommendations=["Add more framework keywords."],
            details={"keyword_score": 85.0, "semantic_score": 85.0},
            model_version="1.0"
        )
        
        response = await async_client.post(
            "/api/v1/matching/score",
            json={"resume_id": str(mock_resume.id), "job_id": str(mock_job.id)}
        )
        
        assert response.status_code == 200
        assert response.json()["score"] == 85.0
        assert "python" in response.json()["matched_skills"]

@pytest.mark.asyncio
async def test_compute_match_score_unparsed_resume(async_client, mock_db_session):
    mock_resume = Resume(id=uuid.uuid4(), user_id=uuid.uuid4())
    # ParsedResume returns None
    mock_scalar = mock_db_session.execute.return_value.scalar_one_or_none
    mock_scalar.side_effect = [mock_resume, None]
    
    response = await async_client.post(
        "/api/v1/matching/score",
        json={"resume_id": str(mock_resume.id), "job_id": str(uuid.uuid4())}
    )
    assert response.status_code == 409
    assert "not been parsed" in response.json()["detail"]
