from typing import Any
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from main import app
from routers.auth import get_current_user
from tests.conftest import register_and_switch_to_new_user


@pytest.fixture(scope="function")
def client_data_for_update() -> dict[str, str]:
    return {
        "name": "new_string",
        "dic": "CZ7082783024",
        "city": "new_city_string",
        "psc": "new_psc_string",
        "street": "new_street_string",
        "house_number": "new_house_string",
        "email": "new_user@example.com",
        "phone_number": "123456789",
    }


async def test_new_client_data_not_equal(
    valid_client_data: dict[str, Any],
    client_data_for_update: dict[str, str],
) -> None:

    for key in client_data_for_update.keys():
        assert client_data_for_update[key] != valid_client_data[key]


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


async def test_get_client_ownership_isolation(
    user_with_one_client, _base_user, user_data
):

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


async def test_delete_client_ownership_isolation(
    user_with_one_client, _base_user, user_data
):

    user, client_id = user_with_one_client
    user_override = app.dependency_overrides.pop(get_current_user)

    new_email = f"new_{user_data['email']}"
    new_user_data = user_data.copy()
    new_user_data["email"] = new_email

    create_new_user = await _base_user.post("/auth/register", json=new_user_data)
    new_user_id = create_new_user.json()["UID"]

    try:
        app.dependency_overrides[get_current_user] = lambda: {"uid": new_user_id}
        response = await _base_user.delete(f"/clients/{client_id}")
    finally:
        app.dependency_overrides[get_current_user] = user_override

    status_code = response.status_code
    data = response.json()

    assert status_code == 404
    assert "not found" in data["detail"].lower()

    client_exist = await user.get(f"/clients/{client_id}")

    assert client_exist.status_code == 200


async def test_get_ico_success(user):

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "obchodniJmeno": "Firma s.r.o.",
        "ico": "12345678",
        "sidlo": {"nazevObce": "Praha", "psc": "11000"},
    }

    mock_client_instance = Mock()
    mock_client_instance.get = AsyncMock(return_value=fake_response)

    mock_async_client_class = MagicMock()
    mock_async_client_class.return_value.__aenter__ = AsyncMock(
        return_value=mock_client_instance
    )

    with patch("routers.clients.httpx.AsyncClient", mock_async_client_class):
        response = await user.get("/clients/ares/12345678")

    assert response.status_code == 200


async def test_get_ico_not_found(user):
    fake_response = Mock()
    fake_response.status_code = 404

    mock_client = Mock()
    mock_client.get = AsyncMock(return_value=fake_response)

    mock_httpx_client_instance = AsyncMock()
    mock_httpx_client_instance.__aenter__ = AsyncMock(return_value=mock_client)

    mock_httpx_client_class = MagicMock(return_value=mock_httpx_client_instance)

    with patch("routers.clients.httpx.AsyncClient", mock_httpx_client_class):
        response = await user.get("/clients/ares/12345678")

    assert response.status_code == 404


async def test_get_ico_unauthorized(unauthorized_user):

    response = await unauthorized_user.get("/clients/ares/12345678")

    assert response.status_code == 401


async def test_update_client_success_with_all_fields(
    user_with_one_client: tuple[AsyncClient, int],
    client_data_for_update: dict[str, str],
) -> None:

    user, client_id = user_with_one_client

    response = await user.patch(f"/clients/{client_id}", json=client_data_for_update)

    response_status_code = response.status_code
    response_json = response.json()

    for key in client_data_for_update.keys():
        assert response_json[key] == client_data_for_update[key]

    assert response_status_code == 200


async def test_update_client_success_one_field(
    user_with_one_client: tuple[AsyncClient, int],
    valid_client_data: dict[str, Any],
    client_data_for_update: dict[str, str],
) -> None:
    user, client_id = user_with_one_client

    new_name = client_data_for_update["name"]
    response = await user.patch(f"/clients/{client_id}", json={"name": new_name})

    response_status_code = response.status_code
    response_json = response.json()

    for key in response_json.keys():
        if key == "name":
            assert response_json[key] == new_name
        elif key == "id":
            assert response_json[key] == client_id
        else:
            assert response_json[key] == valid_client_data[key]

    assert response_status_code == 200


async def test_update_client_cache_changed(
    user_with_one_client: tuple[AsyncClient, int],
    client_data_for_update: dict[str, str],
) -> None:

    user, client_id = user_with_one_client

    await user.get(f"/clients/{client_id}")
    await user.patch(f"/clients/{client_id}", json=client_data_for_update)
    response = await user.get(f"/clients/{client_id}")

    response_status_code = response.status_code
    response_json = response.json()

    for key in client_data_for_update.keys():
        assert response_json[key] == client_data_for_update[key]
    assert response_status_code == 200


async def test_update_client_not_found(
    user: AsyncClient,
) -> None:

    response = await user.patch(f"/clients/999999")

    response_status_code = response.status_code
    response_json = response.json()

    assert response_status_code == 404
    assert "not found" in response_json["detail"].lower()


async def test_update_client_ownership_isolation(
    user_with_one_client: tuple[AsyncClient, int],
    user_data: dict[str, Any],
    valid_client_data: dict[str, Any],
    client_data_for_update: dict[str, str],
) -> None:
    user, client_id = user_with_one_client

    original_override_user = app.dependency_overrides.pop(get_current_user)
    try:
        await register_and_switch_to_new_user(
            user=user, user_data=user_data, email_suffix="2"
        )
        isolation_response = await user.patch(
            f"/clients/{client_id}", json=client_data_for_update
        )
    finally:
        app.dependency_overrides[get_current_user] = original_override_user

    isolation_response_status_code = isolation_response.status_code

    original_user_response = await user.get(f"/clients/{client_id}")
    original_user_response_json = original_user_response.json()

    assert isolation_response_status_code == 404

    for key in valid_client_data.keys():
        assert valid_client_data[key] == original_user_response_json[key]
