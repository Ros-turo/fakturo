from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import uuid4
from typing import Any
from jose import jwt, JWTError

from exceptions import InvalidTokenError, ExpiredTokenError, RevokedTokenError
from settings import settings


def encode_jwt_token(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.secret_key, settings.algorithm)


def decode_jwt_token(token: str) -> dict[str, Any]:

    try:
        payload = jwt.decode(token, settings.secret_key, settings.algorithm)
    except JWTError:
        raise InvalidTokenError()

    return payload


def create_access_token(email: str, uid: int) -> str:
    """
    ::param user data: email, password
    ::return user's token
    """
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(minutes=30)
    jti = str(uuid4())
    payload = {
        "sub": email,
        "jti": jti,
        "uid": uid,
        "iat": now,
        "exp": expire_time,
        "type": "access",
    }

    return encode_jwt_token(payload)


def create_refresh_token(uid: int) -> str:
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(days=15)
    jti = token_urlsafe(32)
    payload = {
        "uid": uid,
        "jti": jti,
        "iat": now,
        "exp": expire_time,
        "type": "refresh",
    }

    return encode_jwt_token(payload)

def check_refresh_token(expired_at: datetime, revoked: bool) -> bool:

    now = datetime.now(timezone.utc)
    if expired_at < now:
        raise ExpiredTokenError()
    if revoked:
        raise RevokedTokenError()

    return True
