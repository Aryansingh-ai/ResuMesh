import pytest
from unittest.mock import patch, AsyncMock
import httpx

@pytest.mark.asyncio
async def test_register_success(async_client, mock_db_session):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Mock Supabase Auth Signup Response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "user": {"id": "123e4567-e89b-12d3-a456-426614174000"},
            "session": {
                "access_token": "fake_access_token",
                "refresh_token": "fake_refresh_token"
            }
        }
        
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "password123", "full_name": "New User"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["access_token"] == "fake_access_token"
        assert data["email"] == "newuser@example.com"

@pytest.mark.asyncio
async def test_register_invalid_password(async_client):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "123", "full_name": "New User"}
    )
    assert response.status_code == 422 # Validation error for password < 8 chars

@pytest.mark.asyncio
async def test_login_success(async_client, mock_db_session):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "fake_access_token",
            "refresh_token": "fake_refresh_token",
            "user": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "testuser@example.com",
                "user_metadata": {"full_name": "Test User"}
            }
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "fake_access_token"

@pytest.mark.asyncio
async def test_login_failure(async_client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"error_description": "Invalid login credentials"}
        
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
