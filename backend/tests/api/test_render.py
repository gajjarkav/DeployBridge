import pytest
import httpx
from unittest.mock import patch
from src.core.crypto import encrypt_secret

@pytest.mark.asyncio
@patch("src.services.render.RenderService.validate_key_and_resolve_owner")
async def test_connect_render(mock_validate, client: httpx.AsyncClient, auth_headers: dict):
    mock_validate.return_value = {"id": "tea-123", "email": "test@example.com"}
    
    response = await client.post(
        "/v1/render/connect",
        json={"api_key": "fake_render_key"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["connected"] == True
    assert response.json()["owner_id"] == "tea-123"

@pytest.mark.asyncio
async def test_render_status(client: httpx.AsyncClient, auth_headers: dict):
    # Depending on order, might be connected or not, but typically we just hit the endpoint
    response = await client.get("/v1/render/status", headers=auth_headers)
    assert response.status_code == 200
    assert "connected" in response.json()

@pytest.mark.asyncio
async def test_disconnect_render(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.delete("/v1/render/connect", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["connected"] == False

@pytest.mark.asyncio
@patch("src.api.v1.render._require_render_key")
@patch("src.services.render.RenderService.list_services")
async def test_list_render_services(mock_list, mock_require_key, client: httpx.AsyncClient, auth_headers: dict):
    mock_require_key.return_value = "fake_key"
    mock_list.return_value = []
    
    response = await client.get("/v1/render/services", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
