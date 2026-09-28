from datetime import datetime, timezone
import time
from typing import Any
from starlette.requests import Request

from cache import set_cache
from db_models import RefreshToken
from exceptions import RefreshTokenNotFoundError, InvalidTokenError
from repositories.interfaces import RefreshTokenGetter, RefreshTokenWriter
from security.tokens import (
    create_refresh_token,
    decode_jwt_token,
    create_access_token,
)


async def refresh_token_to_db(
    refresh_token: str,
    token_writer: RefreshTokenWriter,
    email: str,
) -> None:
    payload = decode_jwt_token(refresh_token)
    jti = payload["jti"]
    user_id = payload["uid"]
    expired_at = datetime.fromtimestamp(float(payload["exp"]), tz=timezone.utc)

    refresh_token_db_instance = RefreshToken(
        jti=jti,
        user_id=user_id,
        user_email=email,
        expired_at=expired_at,
    )

    await token_writer.post_refresh_token(refresh_token_db_instance)


async def create_token_tuple(
    email: str, uid: int, token_writer: RefreshTokenWriter
) -> tuple[str, str]:

    access_token = create_access_token(email=email, uid=uid)
    refresh_token = create_refresh_token(uid=uid)
    await refresh_token_to_db(refresh_token, token_writer, email=email)

    return access_token, refresh_token


async def blacklist_access_token(token: str | None) -> None:

    if token:
        await add_token_to_blacklist(token)


def get_refresh_token_payload(request: Request) -> dict[str, Any]:

    token = request.cookies.get("refresh_token", None)
    if token is None:
        raise RefreshTokenNotFoundError()

    payload = decode_jwt_token(token)

    if payload["type"] != "refresh":
        raise InvalidTokenError()

    return payload


async def get_refresh_token_instance(request: Request, refresh_token_repo: RefreshTokenGetter) -> RefreshToken:

    payload = get_refresh_token_payload(request=request)
    jti = payload["jti"]
    refresh_token = await refresh_token_repo.get_refresh_token(jti)
    if refresh_token is None:
        raise RefreshTokenNotFoundError()

    return refresh_token



async def add_token_to_blacklist(token: str) -> None:

    try:
        payload = decode_jwt_token(token)
    except InvalidTokenError:
        return None
    jti = payload["jti"]
    exp = payload["exp"]
    ttl = int(exp - time.time())
    if ttl > 0:
        await set_cache(key=f"blacklist:{jti}", value="1", ttl=ttl)
    return None


def extract_access_token(request: Request) -> str | None:

    value = request.headers.get("Authorization")

    if value is None:
        return None

    token = value.removeprefix("Bearer ")
    return token
