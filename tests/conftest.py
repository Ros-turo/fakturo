import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from settings import settings
from main import app
from database import Base, get_db
from routers.auth import get_current_user


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
async def client(db):

    def get_override_db():
        yield db

    app.dependency_overrides[get_db] =get_override_db
    app.dependency_overrides[get_current_user] = lambda: {"uid": 1}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def unauthorized_client():

    def get_override_db():
        yield db

    app.dependency_overrides[get_db] = get_override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url = "http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()