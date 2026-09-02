from datetime import datetime, timedelta, timezone
from typing import Annotated
from secrets import token_urlsafe
from fastapi import Depends, HTTPException, Request

from cache import add_token_to_blacklist
from repositories.auth_repository import AuthRepo
from security.tokens import AccessTokenExtractor, decode_jwt_token, encode_jwt_token, create_access_token


async def create_refresh_token(email: str, uid: int, auth_repo: AuthRepo):
    now = datetime.now(timezone.utc)
    expire_time = now + timedelta(days=15)
    jti = token_urlsafe(32)
    payload = {
        'uid': uid,
        'jti': jti,
        'iat': now,
        'exp': expire_time,
        'type': 'refresh'
    }

    token = encode_jwt_token(payload)

    await auth_repo.post_refresh_token(uid=uid, email=email,
                                      jti=jti, expired_at=expire_time)

    return token

async def create_token_tuple(email:str, uid: int, auth_repo: AuthRepo) -> tuple[str,str]:

    access_token = create_access_token(email=email, uid=uid)
    refresh_token = await create_refresh_token(email=email, uid=uid, auth_repo= auth_repo)

    return access_token, refresh_token

async def blacklist_token(token: AccessTokenExtractor) -> None:

    if token:
        await add_token_to_blacklist(token)

AddTokenBlacklist = Annotated[None, Depends(blacklist_token)]

def get_refresh_token_payload(request:Request) -> dict:

    token = request.cookies.get("refresh_token", None)
    if token is None:
        raise HTTPException(status_code=401, detail="Refresh token not found")


    payload = decode_jwt_token(token)

    return payload