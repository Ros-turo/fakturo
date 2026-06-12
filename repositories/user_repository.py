from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db_models import User




class UserRepository:

    def __init__(self,db: AsyncSession):
        self.db = db


    async def create_user(self, new_user: User)->User:

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        return new_user

    async def get_by_email(self, email:str)-> User | None:

        user = await self.db.execute(select(User).where(User.email == email))
        return user.scalar_one_or_none()

