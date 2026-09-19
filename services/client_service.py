from typing import Any

from cache import get_cache, set_cache, delete_cache
from db_models import Client
from exceptions import ClientNotFoundError
from repositories.interfaces import ClientCRUD
from schemas import ClientResponse


async def is_client_in_cache(
    client_id: int,
    uid: int,
) -> str | None:
    key = f"user_{uid}:clients:{client_id}"
    cache_data = await get_cache(key=key)
    return cache_data


async def client_cache_getter(
    client_id: int, uid: int, client_repo: ClientCRUD
) -> ClientResponse:

    cache_data = await is_client_in_cache(client_id=client_id, uid=uid)
    if cache_data:
        response = ClientResponse.model_validate_json(json_data=cache_data)
    else:
        client = await client_repo.get_one_client(client_id=client_id, uid=uid)
        if not client:
            raise ClientNotFoundError(client_id=client_id)
        response = ClientResponse.model_validate(client)
        await client_cache_setter(client=response, uid=uid, ttl=600)
    return response


async def client_cache_setter(client: ClientResponse, uid: int, ttl: int) -> None:
    key = f"user_{uid}:clients:{client.id}"
    value = client.model_dump_json()
    await set_cache(key=key, value=value, ttl=ttl)


async def client_cache_deleter(
    client: Client, uid: int, client_repo: ClientCRUD
) -> None:
    key = f"user_{uid}:clients:{client.id}"
    await client_repo.delete_client(client)
    await delete_cache(key=key)


def ares_parsing(data: dict) -> dict[str, Any]:
    dic = data.get("dic", None)
    street = data["sidlo"].get("nazevUlice", None)
    house_number = data["sidlo"].get("cisloDomovni", None)
    return {
        "name": data["obchodniJmeno"],
        "ico": data["ico"],
        "dic": dic,
        "vat": bool(dic),
        "city": data["sidlo"]["nazevObce"],
        "psc": data["sidlo"]["psc"],
        "street": street,
        "house_number": house_number,
    }
