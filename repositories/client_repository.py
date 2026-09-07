from sqlalchemy import select
from sqlalchemy.orm.exc import StaleDataError

from db_models import Client
from repositories.base_repository import BaseRepo


class ClientRepo(BaseRepo):


    async def get_all_clients(self, uid: int)-> list[Client]:
        clients = await self.db.execute(select(Client).where(Client.owner_id == uid))
        return list(clients.scalars().all())

    async def get_one_client(self,uid: int, client_id: int)-> Client | None:
        client = await self.db.execute(select(Client).where(Client.id ==client_id, Client.owner_id == uid))
        return client.scalar_one_or_none()

    async def create_client(self, new_client: Client) -> Client:

        self.db.add(new_client)
        await self.db.commit()
        await self.db.refresh(new_client)

        return new_client

    async def update_client_name(self, uid:int, client_id:int, new_client_name: str) -> Client | None:

        stmt = select(Client).where(Client.owner_id == uid, Client.id == client_id)
        client = (await self.db.execute(stmt)).scalar_one_or_none()

        if client is None:
            return None

        client.name = new_client_name

        try:
            await self.db.commit()
        except StaleDataError:
            await self.db.rollback()
            raise ValueError("This client version is deprecated")
        return client

    async def delete_client(self, uid:int, client_id: int) -> Client | None:
        result = await self.db.execute(select(Client).where(Client.id == client_id,
                                                              Client.owner_id == uid))
        client = result.scalar_one_or_none()
        if client:
            await self.db.delete(client)
            await self.db.commit()
        return client