from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import Annotated
from config import db_url

engine = create_async_engine(db_url)

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