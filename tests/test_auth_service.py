from datetime import datetime, timedelta

from db_models import RefreshToken
from security.tokens import create_refresh_token, decode_jwt_token
from services.auth_service import refresh_token_to_db


class FakeRefreshTokenWriter:
    def __init__(self):
        self.fake_db = {}

    async def post_refresh_token(self, refresh_token: RefreshToken) -> None:
        uid = refresh_token.user_id
        self.fake_db[uid] = refresh_token


async def test_refresh_token_to_db():
    fake_writer = FakeRefreshTokenWriter()

    refresh_token = create_refresh_token(uid=1)
    payload = decode_jwt_token(refresh_token)
    uid = payload["uid"]
    jti = payload["jti"]

    await refresh_token_to_db(refresh_token, fake_writer, email="ros@email.com")

    refresh_token_in_db = fake_writer.fake_db[uid]

    assert isinstance(fake_writer.fake_db[1], RefreshToken)
    assert refresh_token_in_db.user_id == uid
    assert refresh_token_in_db.jti == jti
    assert refresh_token_in_db.user_email == "ros@email.com"
