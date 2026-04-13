from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_environment_settings
from app.models.orm import Base


@lru_cache
def get_engine(database_url: str | None = None) -> AsyncEngine:
    env = get_environment_settings()
    return create_async_engine(database_url or env.database_url, future=True, pool_pre_ping=True)


@lru_cache
def get_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(database_url), expire_on_commit=False)


async def init_models(database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
