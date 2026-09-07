import asyncio
import time

import redis.asyncio as redis
from typing import Any, cast
from jose import jwt, JWTError

from settings import settings

r = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

async def get_cache(key: str) -> str | None:
    response = await r.get(key)
    if response is None:
        return None
    else:
        return cast(str, response)

async def set_cache(key: str, value: str, ttl: int) -> bool:
    response = await r.set(key, value, ex = ttl)
    return cast(bool, response)

async def delete_cache(key:str) -> int:
    response = await r.delete(key)
    return response

async def add_token_to_blacklist(token:str) -> None:

    try:
        payload = jwt.decode(token, settings.secret_key, settings.algorithm)
    except JWTError:
        return None
    jti = payload['jti']
    exp = payload['exp']
    ttl = int(exp - time.time())
    if ttl > 0:
        await r.set(f'blacklist:{jti}', 1, ex = ttl)
    return None

async def is_token_in_blacklist(jti:str) -> bool:

    response = await r.get(f'blacklist:{jti}')
    if response is None:
        return False
    return True

async def acquire_lock(key:str, ttl:int) -> bool:

    response = await r.set(f'lock:{key}', "1", nx=True, ex=ttl)
    return bool(response)

async def release_lock(key:str) -> None:

    await r.delete(f"lock:{key}")