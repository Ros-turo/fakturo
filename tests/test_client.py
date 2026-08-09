from unittest.mock import Mock, AsyncMock, MagicMock, patch
from main import app
from routers.auth import get_current_user

async def test_empty_clients_list(user):

    response = await user.get("/clients/")

    data = response.json()
    status_code = response.status_code

    assert status_code == 200
    assert data == []

async def test_create_client(user, valid_client_data):


    response = await user.post("/clients/", json=valid_client_data)

    assert response.status_code == 201

    get_clients_from_db = await user.get("/clients/")
    clients_from_db = get_clients_from_db.json()

    assert len(clients_from_db) == 1

    client_from_db = clients_from_db[0]

    assert client_from_db["name"] == valid_client_data["name"]
    assert client_from_db["email"] == valid_client_data["email"]
    assert client_from_db["ico"] == valid_client_data["ico"]

async def test_get_client_success(user_with_one_client, valid_client_data):

    user, client_id = user_with_one_client

    get_client_from_db = await user.get(f"/clients/{client_id}")

    status_code = get_client_from_db.status_code
    data = get_client_from_db.json()

    assert status_code == 200
    assert data["name"] == valid_client_data["name"]
    assert data["email"] == valid_client_data["email"]
    assert data["ico"] == valid_client_data["ico"]

async def test_get_client_not_found(user):

    get_client_from_db = await user.get(f"/clients/999999")

    status_code = get_client_from_db.status_code
    data = get_client_from_db.json()

    assert status_code == 404
    assert data == {"detail": "Client 999999 is not found"}

async def test_get_client_ownership_isolation(user_with_one_client, _base_user, user_data):

    _, client_id = user_with_one_client

    new_email = f"new_{user_data['email']}"
    new_user_data = user_data.copy()
    new_user_data["email"] = new_email
    response = await _base_user.post("auth/register", json=new_user_data)
    new_user_id = response.json()["UID"]

    try:
        app.dependency_overrides[get_current_user] = lambda: {"uid": new_user_id}
        get_client_from_db = await _base_user.get(f"/clients/{client_id}")
    finally:
        app.dependency_overrides.pop(get_current_user)

    assert get_client_from_db.status_code == 404

async def test_delete_client_success(user_with_one_client):

    user, client_id = user_with_one_client
    response_delete = await user.delete(f"/clients/{client_id}")
    response_not_found = await user.get(f"/clients/{client_id}")

    status_code_delete = response_delete.status_code
    status_code_not_found = response_not_found.status_code

    assert status_code_delete == 204
    assert status_code_not_found == 404

async def test_delete_client_not_found(user):

    response = await user.delete("/clients/999999")
    status_code_not_found = response.status_code

    assert status_code_not_found == 404

async def test_delete_client_ownership_isolation(user_with_one_client, _base_user, user_data):

    user, client_id = user_with_one_client
    user_override = app.dependency_overrides.pop(get_current_user)

    new_email = f"new_{user_data['email']}"
    new_user_data = user_data.copy()
    new_user_data["email"] = new_email

    create_new_user = await _base_user.post("/auth/register", json= new_user_data)
    new_user_id = create_new_user.json()["UID"]


    try:
        app.dependency_overrides[get_current_user] = lambda: {"uid": new_user_id}
        response = await _base_user.delete(f"/clients/{client_id}")
    finally:
        app.dependency_overrides[get_current_user] = user_override

    status_code = response.status_code
    data = response.json()

    assert status_code == 404
    assert data == {"detail": "Not found"}


    client_exist = await user.get(f"/clients/{client_id}")

    assert client_exist.status_code == 200


async def test_get_ico_success(user):

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
        response = await user.get("/clients/ares/12345678")

    assert response.status_code == 200


async def test_get_ico_unauthorized(unauthorized_user):

    response = await unauthorized_user.get("/clients/ares/12345678")

    assert response.status_code == 401

