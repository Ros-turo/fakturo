from datetime import datetime, timedelta

from security.tokens import decode_jwt_token
from services.auth_service import create_refresh_token

class FakeRefreshTokenWriter:

    def __init__(self):
        self.fake_db = {}

    async def post_refresh_token(self, uid: int, jti: str,
                                 expired_at: datetime, email: str) -> None:
        self.fake_db[uid] = {"jti": jti, "expired_at": expired_at, "email": email}

async def test_create_refresh_token_success() -> None:

    fake_writer = FakeRefreshTokenWriter()
    token = await create_refresh_token(
        email='ros@example.com',
        uid=1,
        token_writer=fake_writer)

    payload = decode_jwt_token(token)
    jti = payload['jti']

    fake_db = fake_writer.fake_db

    assert payload["uid"] == 1

    assert len(fake_db) == 1
    assert fake_db[1]["jti"] == jti

async def test_token_expire_time_success() -> None:
    fake_writer = FakeRefreshTokenWriter()
    token = await create_refresh_token(
        email='ros@example.com',
        uid=1,
        token_writer=fake_writer)

    payload = decode_jwt_token(token)
    now = payload['iat']
    expired_at = payload['exp']
    delta = expired_at - now

    assert delta == 15*24*60*60
