import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login(client:AsyncClient, registered_user):
    response = await client.post("/auth/login", data={**registered_user})
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client:AsyncClient, registered_user):
    response = await client.post("/auth/login", data={"username":registered_user["username"], "password": "badpassword"})
    assert response.status_code == 401