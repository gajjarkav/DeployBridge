import pytest
import httpx
from unittest.mock import patch

@pytest.mark.asyncio
async def test_get_agent_sessions(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.get("/v1/agent/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()

@pytest.mark.asyncio
async def test_get_agent_sessions_unauthorized(client: httpx.AsyncClient):
    response = await client.get("/v1/agent/sessions")
    assert response.status_code == 401
