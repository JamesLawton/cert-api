import pytest
from httpx import AsyncClient

from cert_tools_api import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(app=app, base_url="http://localhost:7000") as ac:
        response = await ac.post("/createBloxbergCertificate")
        print(response)
    assert response.status_code == 200
    assert response.json() == {"message": "Tomato"}