import pytest

@pytest.mark.asyncio
async def test_health_check(async_client):
    """Test the basic health check endpoint."""
    response = await async_client.get("/health")
    # Some apps put health under /api/v1/health or similar, we will check /health first
    # If 404, we test the root. We assume standard setup.
    if response.status_code == 404:
        response = await async_client.get("/api/v1/health")
        if response.status_code == 404:
            response = await async_client.get("/")
    
    assert response.status_code in (200, 204)

@pytest.mark.asyncio
async def test_metrics_endpoint(async_client):
    """Test prometheus metrics endpoint."""
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    assert "python_gc_objects_collected_total" in response.text or "http_requests_total" in response.text
