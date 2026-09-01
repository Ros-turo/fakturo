import pytest
from database import get_db
from db_models import User

from sqlalchemy import select

def login_data(data):
    email = data['email']
    password = data['password']
    return {"username": email, "password": password}

async def test_register_success(unauthorized_user, user_data):

    response = await unauthorized_user.post("/auth/register", json=user_data)

    print(response.json())
    status_code = response.status_code
    response_json = response.json()
    status = response_json["status"]
    uid = response_json["UID"]

    assert status_code == 201
    assert status == 'ok'
    assert "UID" in response_json


async def test_register_fail(user, unauthorized_user, user_data):

    response = await unauthorized_user.post("/auth/register", json=user_data)

    response_json = response.json()
    status_code = response.status_code

    assert status_code == 400
    assert response_json['detail'] == 'Account with this email already exist'

async def test_not_plain_password_save(user, user_data, db):

    result = await db.execute(select(User).where(User.email == user_data['email']))
    user_db = result.scalar_one()

    assert user_db.hashed_password != user_data['password']

async def test_login_success(user, user_data):

    data = login_data(user_data)
    response = await user.post("/auth/login", data=data)

    status_code = response.status_code
    response_json = response.json()

    assert status_code == 200
    assert "access_token" in response_json

@pytest.mark.parametrize(argnames='credential', argvalues=['password', 'username'], ids=["password", "username"])
async def test_login_wrong_credentials(user, user_data, credential):

    data = login_data(user_data)
    data[credential] = '123'

    response = await user.post("/auth/login", data=data)
    print(response.json())
    status_code = response.status_code
    detail = response.json()['detail']

    assert status_code == 401
    assert detail == 'Invalid credentials'
