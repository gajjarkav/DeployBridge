import pytest
import httpx
from unittest.mock import patch

@pytest.mark.asyncio
async def test_get_github_login_url(client: httpx.AsyncClient):
    response = await client.get("/v1/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert "login_url" in data
    assert "state" in data
    assert "https://github.com/login/oauth/authorize" in data["login_url"]

@pytest.mark.asyncio
@patch("src.services.github.GitHubService.get_access_token")
@patch("src.services.github.GitHubService.get_user_profile")
async def test_github_callback(mock_get_profile, mock_get_token, client: httpx.AsyncClient):
    mock_get_token.return_value = {
        "access_token": "fake_token",
        "token_type": "bearer",
        "scope": "repo"
    }
    mock_get_profile.return_value = {
        "github_id": 9999,
        "username": "newuser",
        "email": "newuser@example.com",
        "avatar_url": "https://example.com/avatar.png"
    }
    
    response = await client.get("/v1/auth/callback?code=fake_code")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful"
    assert "session_token" in data
    assert data["user"]["username"] == "newuser"

@pytest.mark.asyncio
async def test_get_user_profile_unauthorized(client: httpx.AsyncClient):
    response = await client.get("/v1/auth/profile")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_user_profile(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.get("/v1/auth/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_update_user_profile(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.patch(
        "/v1/auth/profile", 
        json={"deploy_branch": "main"}, 
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deploy_branch"] == "main"

@pytest.mark.asyncio
async def test_refresh_session(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.post("/v1/auth/refresh", headers=auth_headers)
    assert response.status_code == 200
    assert "session_token" in response.json()

@pytest.mark.asyncio
async def test_logout(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.post("/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Logged out"}
