from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Path
from httpx import Response as httpx_Response
from starlette import status

from database import DBSession
from db_models import Client
from exceptions import ARESICONotFoundError, ARESNotAvailableError, ClientNotFoundError
from repositories.client_repository import ClientRepo
from repositories.interfaces import ClientCRUD, ClientListing
from routers.auth import UserID, get_current_user
from schemas import ClientAres, ClientCreate, ClientResponse, ClientUpdate
from services.client_service import (
    client_cache_deleter,
    client_cache_getter,
    client_cache_setter,
    ares_parsing,
)

router = APIRouter(prefix="/clients", tags=["clients"])


def get_client_repo(db: DBSession) -> ClientRepo:
    return ClientRepo(db)


ClientCRUDDepends = Annotated[ClientCRUD, Depends(get_client_repo)]
ClientListingDepends = Annotated[ClientListing, Depends(get_client_repo)]


async def client_getter(
    client_id: int, uid: UserID, client_repo: ClientCRUDDepends
) -> Client:
    client = await client_repo.get_one_client(uid=uid, client_id=client_id)
    if client is None:
        raise ClientNotFoundError(client_id=client_id)
    return client


ClientGetDepends = Annotated[Client, Depends(client_getter)]


async def ares_request(
    ico: str,
) -> httpx_Response:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
            )
        except httpx.RequestError:
            raise ARESNotAvailableError()
    if response.status_code == 404:
        raise ARESICONotFoundError()
    return response


async def create_client_composition(
    uid: UserID, data: ClientCreate, repo: ClientCRUDDepends
) -> Client:

    client = Client(**data.model_dump(), owner_id=uid)
    created_client = await repo.create_client(client)

    return created_client


ClientCreateDepends = Annotated[Client, Depends(create_client_composition)]


@router.get(
    "/ares/{ico}", response_model=ClientAres, dependencies=[Depends(get_current_user)]
)
async def get_ico(ico: Annotated[str, Path(pattern=r"\d{8}")]) -> ClientAres:
    ares_response = await ares_request(ico=ico)
    ares_json = ares_response.json()
    new_client = ClientAres(**ares_parsing(ares_json))
    return new_client


@router.get("/", response_model=list[ClientResponse], status_code=200)
async def get_clients(uid: UserID, repo: ClientListingDepends) -> list[Client]:

    clients = await repo.get_all_clients(uid)
    return clients


@router.get("/{client_id}", response_model=ClientResponse, status_code=200)
async def get_client(
    client_id: int, uid: UserID, repo: ClientCRUDDepends
) -> ClientResponse:

    response = await client_cache_getter(client_id=client_id, uid=uid, client_repo=repo)
    return response


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreateDepends,
    uid: UserID,
) -> ClientResponse:

    response = ClientResponse.model_validate(client)
    await client_cache_setter(client=response, uid=uid, ttl=600)

    return response


@router.patch(
    "/{client_id}", response_model=ClientResponse, status_code=status.HTTP_200_OK
)
async def update_client(
    client: ClientGetDepends,
    client_repo: ClientCRUDDepends,
    new_value: ClientUpdate,
    uid: UserID,
) -> ClientResponse:

    raw_updated_client = await client_repo.update_client(
        client=client, new_value=new_value
    )
    updated_client = ClientResponse.model_validate(raw_updated_client)
    await client_cache_setter(client=updated_client, uid=uid, ttl=600)
    return updated_client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    uid: UserID,
    client: ClientGetDepends,
    repo: ClientCRUDDepends,
) -> None:
    await client_cache_deleter(client=client, uid=uid, client_repo=repo)
