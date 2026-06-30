from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.orm import DeclarativeBase
from typing import Annotated
from settings import settings

engine: AsyncEngine = create_async_engine(settings.db_url,
                             pool_size = 2,
                             max_overflow = 3,
                             pool_timeout = 30,
                             pool_recycle = 1800,
                             pool_pre_ping = True)

SessionLocal =  async_sessionmaker(engine, autoflush= False, autocommit= False,expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

DBSession = Annotated[AsyncSession, Depends(get_db)]