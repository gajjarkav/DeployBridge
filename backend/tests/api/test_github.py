import pytest
import httpx
from unittest.mock import patch
from src.core.crypto import encrypt_secret
from src.models.user import User

@pytest.mark.asyncio
@patch("src.services.github.GitHubService.get_repository_info")
async def test_get_repository_info(mock_get_repo_info, client: httpx.AsyncClient, auth_headers: dict):
    mock_get_repo_info.return_value = {
        "success": True,
        "message": "OK",
        "basic_info": {
            "name": "test-repo",
            "owner_login": "test-owner"
        }
    }
    
    response = await client.post(
        "/v1/github/repos/info",
        json={"owner": "test-owner", "repository": "test-repo"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["basic_info"]["name"] == "test-repo"
    assert data["basic_info"]["owner_login"] == "test-owner"

@pytest.mark.asyncio
async def test_get_repository_info_unauthorized(client: httpx.AsyncClient):
    response = await client.post(
        "/v1/github/repos/info",
        json={"owner": "test-owner", "repository": "test-repo"}
    )
    assert response.status_code == 401
