from typing import Annotated

from fastapi import APIRouter, Depends, Path, HTTPException

from repositories.client_repository import ClientRepo
from schemas import ClientCreate, ClientResponse, ClientAres
from routers.auth import CurrentUser
from database import DBSession
from db_models import  Client
import httpx


router = APIRouter(prefix='/clients', tags=['clients'])


def get_client_repo(db: DBSession)-> ClientRepo:
    return ClientRepo(db)

ClientDepends = Annotated[ClientRepo, Depends(get_client_repo)]

def ares_parsing(data:dict):
    dic = data.get("dic",None)
    street = data["sidlo"].get("nazevUlice", None)
    house_number = data["sidlo"].get("cisloDomovni", None)
    return {"name":data["obchodniJmeno"],
            "ico":data["ico"],
            "dic": dic,
            "vat": True if dic else False,
            "city": data["sidlo"]["nazevObce"],
            "psc":data["sidlo"]["psc"],
            "street":street,
            "house_number":house_number}


@router.get('/ares/{ico}', response_model=ClientAres)
async def get_ico(ico: Annotated[str, Path(pattern=r'\d{8}')], user: CurrentUser):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f'https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}')
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="ARES neni dostupny")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="IČO nenalezeno")
    new_client = ClientAres(**ares_parsing(response.json()))
    return new_client

@router.get('/', response_model=list[ClientResponse])
async def get_clients(user: CurrentUser, repo: ClientDepends):
    uid = user["uid"]
    clients: list[Client] = await repo.get_all_clients(uid)
    return clients

@router.get('/{client_id}', response_model=ClientResponse)
async def get_client(client_id: int, user: CurrentUser, repo: ClientDepends):
    uid = user['uid']
    client: Client | None = await repo.get_one_client(uid=uid, client_id=client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Not found")
    return client

@router.post('/', response_model=ClientResponse)
async def create_client(client: ClientCreate, user: CurrentUser,
                  repo: ClientDepends):

    uid = user['uid']
    new_client = Client(**client.model_dump(),
                        owner_id=uid)
    return await repo.create_client(new_client)

@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: int, user:CurrentUser, repo: ClientDepends):
    uid = user["uid"]
    client = await repo.delete_client(uid=uid, client_id=client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Not found")