import pytest
from app.services.embedding_service import EmbeddingService

@pytest.fixture
def embedding_service():
    # Will use sentence_transformers mock if configured, or run the real basic model
    # which is fast enough for local testing, but we can mock encode
    return EmbeddingService()

@pytest.mark.asyncio
async def test_encode_text(embedding_service):
    """Test generating embeddings for a simple string."""
    vector = await embedding_service.encode("Software engineering is fun")
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(x, float) for x in vector)

@pytest.mark.asyncio
async def test_encode_empty_text(embedding_service):
    """Empty text should return 0 vector or standard output without crashing."""
    vector = await embedding_service.encode("")
    assert isinstance(vector, list)
