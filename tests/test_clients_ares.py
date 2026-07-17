from unittest.mock import Mock, AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from routers.auth import get_current_user
from routers.clients import get_client_repo


async def test_get_ico_success(client):

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
                                        "obchodniJmeno": "Firma s.r.o.",
                                        "ico": "12345678",
                                        "sidlo": {"nazevObce": "Praha", "psc": "11000"}
                                    }


    mock_client_instance = Mock()
    mock_client_instance.get = AsyncMock(return_value = fake_response)

    mock_async_client_class = MagicMock()
    mock_async_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)


    with patch("routers.clients.httpx.AsyncClient", mock_async_client_class):
        response = await client.get("/clients/ares/12345678")

    assert response.status_code == 200


async def test_get_ico_unauthorized(unauthorized_client):

    response = await unauthorized_client.get("/clients/ares/12345678")

    assert response.status_code == 401

