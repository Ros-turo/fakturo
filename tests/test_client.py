from unittest.mock import Mock, AsyncMock, MagicMock, patch

async def test_empty_clients_list(client):

    response = await client.get("/clients/")

    data = response.json()
    status_code = response.status_code

    assert status_code == 200
    assert data == []

async def test_create_client(client, valid_client_data):


    response = await client.post("/clients/", json=valid_client_data)

    assert response.status_code == 201

    get_clients_from_db = await client.get("/clients/")

    clients_from_db = get_clients_from_db.json()

    assert len(clients_from_db) == 1

    client_from_db = clients_from_db[0]

    assert client_from_db["name"] == valid_client_data["name"]
    assert client_from_db["email"] == valid_client_data["email"]
    assert client_from_db["ico"] == valid_client_data["ico"]

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

