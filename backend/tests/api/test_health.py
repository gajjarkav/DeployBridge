import pytest
import httpx

@pytest.mark.asyncio
async def test_health_check(client: httpx.AsyncClient):
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "Ok"}
