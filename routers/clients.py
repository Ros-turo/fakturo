from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path

from cache import delete_cache, get_cache, set_cache
from database import DBSession
from db_models import Client
from exceptions import ARESICONotFoundError, ARESNotAvailableError, ClientNotFoundError
from repositories.client_repository import ClientRepo
from repositories.interfaces import ClientCRUD, ClientListing
from routers.auth import CurrentUser, UserID, get_current_user
from schemas import ClientAres, ClientCreate, ClientResponse

router = APIRouter(prefix='/clients', tags=['clients'])


def get_client_repo(db: DBSession)-> ClientRepo:
    return ClientRepo(db)

ClientCRUDDepends = Annotated[ClientCRUD, Depends(get_client_repo)]
ClientListingDepends = Annotated[ClientListing, Depends(get_client_repo)]


async def client_getter(client_id:int, client_repo: ClientCRUD, uid: UserID) -> Client:
    client = await client_repo.get_one_client(uid=uid, client_id=client_id)
    if client is None:
        raise ClientNotFoundError(client_id=client_id)
    return client

ClientGetDepends = Annotated[Client, Depends(client_getter)]


async def create_client_composition(
    uid: UserID, data: ClientCreate, repo: ClientCRUDDepends
) -> Client:

    client = Client(**data.model_dump(), owner_id=uid)
    created_client = await repo.create_client(client)

    return created_client

ClientCreateDepends = Annotated[Client, Depends(create_client_composition)]


def ares_parsing(data:dict):
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
async def get_ico(ico: Annotated[str, Path(pattern=r'\d{8}')]):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}')
        except httpx.RequestError:
            raise ARESNotAvailableError()
    if response.status_code == 404:
        raise ARESICONotFoundError()
    new_client = ClientAres(**ares_parsing(response.json()))
    return new_client

@router.get('/', response_model=list[ClientResponse])
async def get_clients(user: CurrentUser, repo: ClientListingDepends):
    uid = user["uid"]
    clients: list[Client] = await repo.get_all_clients(uid)
    return clients

@router.get('/{client_id}', response_model=ClientResponse)
async def get_client(client_id: int, user: CurrentUser, repo: ClientCRUDDepends):
    uid = user['uid']
    key = f"user_{uid}:clients:{client_id}"

    cache_try = await get_cache(key=key)
    if not (cache_try is None):
        client_data = ClientResponse.model_validate_json(json_data=cache_try)
        return client_data

    client = await repo.get_one_client(uid=uid, client_id=client_id)
    if not client:
        raise ClientNotFoundError(client_id=client_id)

    response = ClientResponse.model_validate(client)
    value = response.model_dump_json()
    await set_cache(key=key, value=value, ttl=600)

    return response


@router.post('/', response_model=ClientResponse, status_code=201)
async def create_client(
        client: ClientCreateDepends,
        uid: UserID,
):

    response = ClientResponse.model_validate(client)
    cache_client = response.model_dump_json()
    key = f"user_{uid}:clients:{client.id}"
    await set_cache(key=key, value=cache_client, ttl=600)

    return response

@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: int, user:CurrentUser, repo: ClientCRUDDepends):
    uid = user["uid"]

    client = await repo.get_one_client(uid=uid, client_id=client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.delete_client(client)

    key = f"user_{uid}:clients:{client_id}"
    await delete_cache(key=key)
