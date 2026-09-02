from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Annotated
from jose import jwt, JWTError
from fastapi import Request, Depends, HTTPException

from settings import settings
from cache import add_token_to_blacklist


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

    return jwt.encode(payload, settings.secret_key, settings.algorithm)


def extract_access_token(request: Request) -> str | None:

    value = request.headers.get("Authorization")

    if value is None:
        return None

    token = value.removeprefix("Bearer ")
    return token

AccessTokenExtractor = Annotated[str|None, Depends(extract_access_token)]

async def blacklist_token(token: AccessTokenExtractor) -> None:

    if token:
        await add_token_to_blacklist(token)

AddTokenBlacklist = Annotated[None, Depends(blacklist_token)]


def check_refresh_token(expired_at: datetime, revoked: bool) -> bool:

    now = datetime.now(timezone.utc)
    if expired_at < now or revoked:
        return False

    return True
def get_refresh_token_payload(request:Request) -> dict:

    token = request.cookies.get("refresh_token", None)
    if token is None:
        raise HTTPException(status_code=401, detail="Refresh token not found")


    payload = decode_jwt_token(token)

    return payload

def decode_jwt_token(token:str) -> dict:

    try:
        payload = jwt.decode(token, settings.secret_key, settings.algorithm)
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return payload
