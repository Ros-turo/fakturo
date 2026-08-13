import redis.asyncio as redis
from typing import cast

r = redis.Redis(host='redis', port=6379)

async def get_cache(key: str) -> str | None:
    response = await r.get(key)
    if response is None:
        return None
    else:
        return str(response)

async def set_cache(key: str, value: str, ttl: int) -> bool:
    response = await r.set(key, value, ex = ttl)
    return cast(bool, response)

async def delete_cache(key:str) -> int:
    response = await r.delete(key)
    return response
