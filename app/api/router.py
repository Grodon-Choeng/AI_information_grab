from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    DigestRequest,
    DigestResponse,
    IngestRequest,
    IngestResponse,
    ItemResponse,
    SourceResponse,
)
from app.container import AppContainer, get_container


router = APIRouter()


def get_app_container() -> AppContainer:
    return get_container()


async def get_session(container: AppContainer = Depends(get_app_container)):
    async with container.session_factory() as session:
        yield session


@router.get("/health")
async def health(container: AppContainer = Depends(get_app_container)) -> dict[str, object]:
    return await container.health_service.check()


@router.post("/runs/ingest", response_model=IngestResponse)
async def run_ingest(
    payload: IngestRequest,
    container: AppContainer = Depends(get_app_container),
) -> IngestResponse:
    result = await container.ingestion_service.ingest(
        sources=payload.sources,
        from_at=payload.from_at,
        to_at=payload.to_at,
    )
    return IngestResponse(**result.__dict__)


@router.post("/runs/digest", response_model=DigestResponse)
async def run_digest(
    payload: DigestRequest,
    container: AppContainer = Depends(get_app_container),
) -> DigestResponse:
    result = await container.digest_service.digest(biz_date=payload.biz_date)
    return DigestResponse(
        run_id=result.run_id,
        biz_date=result.biz_date,
        cluster_count=result.cluster_count,
        llm_used=result.llm_used,
        entries=[entry.__dict__ for entry in result.entries],
    )


@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    biz_date: date | None = Query(default=None),
    source: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    dedup_status: str | None = Query(default=None),
    canonical_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
) -> list[ItemResponse]:
    items = await container.item_repository.list_items(
        session,
        biz_date=biz_date,
        source=source,
        topic=topic,
        dedup_status=dedup_status,
        canonical_only=canonical_only,
    )
    return [
        ItemResponse(
            id=item.id,
            source=item.source,
            source_item_id=item.source_item_id,
            title=item.title,
            author=item.author,
            url=item.url,
            normalized_url=item.normalized_url,
            published_at_utc=item.published_at_utc,
            biz_date=item.biz_date,
            source_score=item.source_score,
            topic_hint=item.topic_hint,
            cluster_id=item.cluster_id,
            dedup_status=item.dedup_status,
        )
        for item in items
    ]


@router.get("/digests/{biz_date}")
async def get_digest(
    biz_date: date,
    session: AsyncSession = Depends(get_session),
    container: AppContainer = Depends(get_app_container),
) -> dict[str, object]:
    digest = await container.item_repository.get_digest_by_date(session, biz_date)
    if digest is None:
        return {"biz_date": biz_date.isoformat(), "found": False}
    return {
        "biz_date": digest.biz_date.isoformat(),
        "generated_at_utc": digest.generated_at_utc.isoformat(),
        "cluster_count": digest.cluster_count,
        "summary_markdown": digest.summary_markdown,
        "payload": digest.payload_json,
    }


@router.get("/sources", response_model=SourceResponse)
async def get_sources(container: AppContainer = Depends(get_app_container)) -> SourceResponse:
    return SourceResponse(
        timezone=container.source_config.timezone,
        llm_enabled=container.source_config.llm.enabled,
        sources=container.source_config.sources.model_dump(),
    )
