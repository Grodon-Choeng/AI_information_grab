from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db import get_session_factory
from app.core.settings import EnvironmentSettings, SourceConfigFile, get_environment_settings, load_source_config
from app.repos.items import ItemRepository
from app.repos.runs import RunRepository
from app.services.digest import DigestService
from app.services.health import HealthService
from app.services.ingestion import IngestionService
from app.services.llm import LLMService
from app.services.source_registry import SourceRegistry


@dataclass
class AppContainer:
    env: EnvironmentSettings
    source_config: SourceConfigFile
    session_factory: async_sessionmaker
    source_registry: SourceRegistry
    item_repository: ItemRepository
    run_repository: RunRepository
    llm_service: LLMService
    ingestion_service: IngestionService
    digest_service: DigestService
    health_service: HealthService


@lru_cache
def get_container() -> AppContainer:
    env = get_environment_settings()
    source_config = load_source_config()
    session_factory = get_session_factory(env.database_url)
    source_registry = SourceRegistry(source_config)
    item_repository = ItemRepository(source_config.timezone)
    run_repository = RunRepository()
    llm_service = LLMService(source_config.llm)
    ingestion_service = IngestionService(session_factory, source_registry, item_repository, run_repository)
    digest_service = DigestService(
        session_factory,
        item_repository,
        run_repository,
        llm_service,
        source_config.dedup,
    )
    health_service = HealthService(session_factory, llm_service)
    return AppContainer(
        env=env,
        source_config=source_config,
        session_factory=session_factory,
        source_registry=source_registry,
        item_repository=item_repository,
        run_repository=run_repository,
        llm_service=llm_service,
        ingestion_service=ingestion_service,
        digest_service=digest_service,
        health_service=health_service,
    )
