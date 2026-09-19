import pytest
import httpx
from unittest.mock import patch

@pytest.mark.asyncio
async def test_get_reports(client: httpx.AsyncClient, auth_headers: dict):
    response = await client.get("/v1/reports/history", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()

@pytest.mark.asyncio
async def test_get_reports_unauthorized(client: httpx.AsyncClient):
    response = await client.get("/v1/reports/history")
    assert response.status_code == 401
