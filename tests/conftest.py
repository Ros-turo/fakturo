from typing import Any, Generator, AsyncGenerator, cast
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from settings import settings
from main import app
from database import Base, get_db
from routers.auth import get_current_user
from security.rate_limit import attempt_logger

@pytest.fixture(scope="function")
def user_data() -> dict[str,str]:
    return {
        "password": "stringst",
        "email": "user@example.com",
        "name": "string",
        "surname": "string",
        "ico": "14044984",
        "dic": "SK22500300",
        "city": "string",
        "psc": "string",
        "street": "string",
        "house_number": "string"
    }

@pytest.fixture(scope="function")
def valid_client_data() -> dict[str, Any]:
    return {
      "name": "string",
      "ico": "91291715",
      "dic": "SK7082783024",
      "city": "string",
      "psc": "string",
      "street": "string",
      "house_number": "string",
      "vat": True,
      "email": "user@example.com",
      "phone_number": "170418643"
    }

@pytest.fixture(autouse=True)
def clear_attempt_logger():
    yield
    attempt_logger.clear()

@pytest.fixture(autouse=True)
def mock_notify_invoice_created():
    with patch("routers.invoices.notify_invoice_created"):
        yield

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(url=settings.test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db(engine):
    async with engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        await conn.begin_nested()

        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(sess, transaction):

            if conn.closed:
                return
            if not conn.in_nested_transaction():
                conn.sync_connection.begin_nested()


        yield session
        await session.close()
        await conn.rollback()

@pytest.fixture(scope="function")
async def _base_user(db:AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def get_override_db() -> Generator[AsyncSession, None, None]:
        yield db
    app.user_middleware = []
    app.middleware_stack = None
    app.dependency_overrides[get_db] = get_override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url = "http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def unauthorized_user(_base_user: AsyncClient) -> AsyncClient:
    return _base_user

@pytest.fixture(scope="function")
async def user(_base_user: AsyncClient, user_data: dict[str, str]) -> AsyncGenerator[AsyncClient, None]:


    response = await _base_user.post("/auth/register", json=user_data)
    uid = response.json()['UID']
    app.dependency_overrides[get_current_user] = lambda: {"uid": uid}
    yield _base_user
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def user_with_one_client(user: AsyncClient, valid_client_data: dict[str, Any]) -> AsyncGenerator[tuple[AsyncClient, int], None]:

    response = await user.post("/clients/", json=valid_client_data)
    client_data = response.json()
    client_id = client_data["id"]

    client_id = int(client_id)

    yield user, client_id


async def register_and_switch_to_new_user(user: AsyncClient,
                                          user_data: dict[str, str],
                                          email_suffix: str) -> int:
    new_user_data = {**user_data, "email": f"{email_suffix}_{user_data['email']}"}
    new_user = await user.post("/auth/register", json=new_user_data)
    new_user_id = new_user.json()["UID"]
    app.dependency_overrides[get_current_user] = lambda: {"uid": new_user_id}
    return cast(int, new_user_id)
