from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import IngestRun


class RunRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        run_type: str,
        source: str | None = None,
        window_start_utc: datetime | None = None,
        window_end_utc: datetime | None = None,
        biz_date: date | None = None,
    ) -> IngestRun:
        run = IngestRun(
            run_type=run_type,
            source=source,
            status="running",
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
            biz_date=biz_date,
        )
        session.add(run)
        await session.flush()
        return run

    async def finish(
        self,
        session: AsyncSession,
        run_id: str,
        *,
        status: str,
        stats: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> IngestRun:
        run = await session.scalar(select(IngestRun).where(IngestRun.id == run_id))
        if run is None:
            raise ValueError(f"run {run_id} not found")
        run.status = status
        run.stats_json = stats or {}
        run.error_json = error or {}
        run.finished_at_utc = datetime.now(tz=UTC)
        await session.flush()
        return run
