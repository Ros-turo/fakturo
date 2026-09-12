import time
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Path
from starlette import status

from cache import delete_cache, get_cache, set_cache
from database import DBSession
from db_models import Client
from exceptions import ARESICONotFoundError, ARESNotAvailableError, ClientNotFoundError
from repositories.client_repository import ClientRepo
from repositories.interfaces import ClientCRUD, ClientListing
from routers.auth import UserID, get_current_user
from schemas import ClientAres, ClientCreate, ClientResponse

router = APIRouter(prefix='/clients', tags=['clients'])


def get_client_repo(db: DBSession)-> ClientRepo:
    return ClientRepo(db)

ClientCRUDDepends = Annotated[ClientCRUD, Depends(get_client_repo)]
ClientListingDepends = Annotated[ClientListing, Depends(get_client_repo)]


async def client_getter(client_id: int, uid: UserID, client_repo: ClientCRUD) -> Client:
    client = await client_repo.get_one_client(uid=uid, client_id=client_id)
    if client is None:
        raise ClientNotFoundError(client_id=client_id)
    return client

ClientGetDepends = Annotated[Client, Depends(client_getter)]

async def client_cache_setter(client: ClientResponse, uid: int, ttl:int) -> None:
    # Take client row from db -> set Redis cache and transform db data into pydantic
    key = f"user_{uid}:clients:{client.id}"
    value = client.model_dump_json()
    await set_cache(key=key, value=value, ttl=ttl)


async def is_client_in_cache(client_id: int, uid: int) -> str | None:
    key = f"user_{uid}:clients:{client_id}"
    data = await get_cache(key=key)
    return data

async def create_client_composition(
        uid: UserID,
        data: ClientCreate,
        repo: ClientCRUDDepends
) -> Client:

    client = Client(**data.model_dump(), owner_id=uid)
    created_client = await repo.create_client(client)

    return created_client

ClientCreateDepends = Annotated[Client, Depends(create_client_composition)]


def ares_parsing(
        data:dict
) -> dict[str, Any]:
    dic = data.get("dic",None)
    street = data["sidlo"].get("nazevUlice", None)
    house_number = data["sidlo"].get("cisloDomovni", None)
    return {"name":data["obchodniJmeno"],
            "ico":data["ico"],
            "dic": dic,
            "vat": bool(dic),
            "city": data["sidlo"]["nazevObce"],
            "psc":data["sidlo"]["psc"],
            "street":street,
            "house_number":house_number}


@router.get('/ares/{ico}', response_model=ClientAres, dependencies=[Depends(get_current_user)])
async def get_ico(
        ico: Annotated[str, Path(pattern=r'\d{8}')]
) -> ClientAres:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}')
        except httpx.RequestError:
            raise ARESNotAvailableError()
    if response.status_code == 404:
        raise ARESICONotFoundError()
    new_client = ClientAres(**ares_parsing(response.json()))
    return new_client

@router.get('/', response_model=list[ClientResponse], status_code=200)
async def get_clients(
        uid: UserID,
        repo: ClientListingDepends
) -> list[Client]:

    clients = await repo.get_all_clients(uid)
    return clients




@router.get('/{client_id}', response_model=ClientResponse, status_code=200)
async def get_client(
        client_id: int,
        uid: UserID,
        repo: ClientCRUDDepends
) -> ClientResponse:

    cache_data = await is_client_in_cache(client_id=client_id, uid=uid)
    if cache_data:
        response = ClientResponse.model_validate_json(json_data=cache_data)
    else:
        time.sleep(1)
        client = await client_getter(client_id=client_id, uid=uid, client_repo=repo)
        response = ClientResponse.model_validate(client)
        await client_cache_setter(client=response, uid=uid, ttl=600)
    return response


@router.post('/', response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
        client: ClientCreateDepends,
        uid: UserID,
) -> ClientResponse:

    response = ClientResponse.model_validate(client)
    await client_cache_setter(client=response, uid=uid, ttl=600)

    return response

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
        uid: UserID,
        client_id: int,
        repo: ClientCRUDDepends,
):
    client = await client_getter(client_id=client_id, uid=uid, client_repo=repo)
    key = f"user_{uid}:clients:{client.id}"
    await repo.delete_client(client)
    await delete_cache(key=key)