import redis.asyncio as redis
from typing import cast
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
