from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from database.db_config import DatabaseConfig
from typing import AsyncGenerator, Annotated
from fastapi import Depends
from database import models

db_url: str = DatabaseConfig().db_url()

engine = create_async_engine(
    db_url,
    echo=True,
    pool_size=15,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:

    async with async_session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_session_factory


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SessionFactoryDep = Annotated[
    async_sessionmaker[AsyncSession], Depends(get_session_factory)
]
