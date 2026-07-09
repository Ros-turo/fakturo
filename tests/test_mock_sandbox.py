
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest


fake_response = MagicMock()
fake_response.status_code = 200
fake_response.json.return_value = {"test":"data"}

mock_client_instance = MagicMock()
mock_client_instance.get = AsyncMock(return_value=fake_response)

mock_async_client_class = MagicMock()
mock_async_client_class.return_value.__aenter__ = AsyncMock(return_value= mock_client_instance)

def test_fake_response():

    assert fake_response.status_code == 200
    assert fake_response.json() == {"test": "data"}

async def test_client_instance():

    async with mock_async_client_class() as mock_func:
        response = await mock_func.get("https://info.cz")

    assert response.status_code == 200
    assert response.json() == {"test":"data"}


# async def test_ares():
#
#     with patch("routers.clients.httpx.AsyncClient") as mock_func:
