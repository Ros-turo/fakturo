from typing import Any

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

    async def create_client(self, client: Client) -> Client:

        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)

        return client

    async def update_client(self, client: Client, new_value: tuple[str, Any]) -> Client:

        key, value = new_value
        setattr(client, key, value)
        try:
            await self.db.commit()
        except StaleDataError:
            await self.db.rollback()
            raise ValueError("This client version is deprecated")
        return client

    async def delete_client(self, client: Client) -> None:
        await self.db.delete(client)
        await self.db.commit()