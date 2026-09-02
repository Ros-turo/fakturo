from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Annotated, Any
from jose import jwt, JWTError
from fastapi import Request, Depends, HTTPException

from settings import settings


def encode_jwt_token(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.secret_key, settings.algorithm)


def decode_jwt_token(token:str) -> dict[str, Any]:

    try:
        payload = jwt.decode(token, settings.secret_key, settings.algorithm)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return payload


def create_access_token(email:str, uid:int) -> str:
    """
    ::param user data: email, password
    ::return user's token
    """
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(minutes=30)
    jti = str(uuid4())
    payload = {
        'sub': email,
        'jti': jti,
        'uid': uid,
        'iat': now,
        'exp': expire_time,
        'type': 'access'
    }

    return encode_jwt_token(payload)


def extract_access_token(request: Request) -> str | None:

    value = request.headers.get("Authorization")

    if value is None:
        return None

    token = value.removeprefix("Bearer ")
    return token

AccessTokenExtractor = Annotated[str|None, Depends(extract_access_token)]


def check_refresh_token(expired_at: datetime, revoked: bool) -> bool:

    now = datetime.now(timezone.utc)
    if expired_at < now or revoked:
        return False

    return True