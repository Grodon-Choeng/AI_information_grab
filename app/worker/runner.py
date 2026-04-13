from __future__ import annotations

from datetime import date, datetime

from app.container import AppContainer
from app.models.domain import DigestResult, IngestResult


class WorkerRunner:
    def __init__(self, container: AppContainer) -> None:
        self.container = container

    async def run_ingest(
        self,
        *,
        sources: list[str] | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> IngestResult:
        return await self.container.ingestion_service.ingest(sources=sources, from_at=from_at, to_at=to_at)

    async def run_digest(self, *, biz_date: date) -> DigestResult:
        return await self.container.digest_service.digest(biz_date=biz_date)
