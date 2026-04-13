from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.settings import DedupConfig, LLMConfig
from app.models.domain import FetchedItem
from app.models.orm import Base
from app.repos.items import ItemRepository
from app.repos.runs import RunRepository
from app.services.digest import DigestService
from app.services.llm import LLMService


@pytest.mark.asyncio
async def test_digest_merges_cross_source_same_url() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    item_repository = ItemRepository("Asia/Shanghai")
    async with session_factory() as session:
        await item_repository.store_fetched_item(
            session,
            FetchedItem(
                source="reddit",
                source_item_id="t3_1",
                title="Agent framework launched",
                url="https://example.com/agent?utm_source=reddit",
                author="alice",
                content_text="",
                published_at_utc=datetime(2026, 4, 13, 3, 0, tzinfo=UTC),
                source_score=10,
                topic_hint="LocalLLaMA",
                payload={},
            ),
        )
        await item_repository.store_fetched_item(
            session,
            FetchedItem(
                source="hackernews",
                source_item_id="123",
                title="Agent framework launched on GitHub",
                url="https://example.com/agent",
                author="bob",
                content_text="",
                published_at_utc=datetime(2026, 4, 13, 4, 0, tzinfo=UTC),
                source_score=15,
                topic_hint="agent",
                payload={},
            ),
        )
        await session.commit()

    service = DigestService(
        session_factory,
        item_repository,
        RunRepository(),
        LLMService(LLMConfig(enabled=False)),
        DedupConfig(title_similarity_threshold=0.75, max_cluster_window_hours=36, min_token_overlap=0.4),
    )
    result = await service.digest(biz_date=date(2026, 4, 13))
    assert result.cluster_count == 1
    assert result.llm_used is False
    assert sorted(result.entries[0].sources) == ["hackernews", "reddit"]
