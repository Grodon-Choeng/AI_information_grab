from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import get_logger, log_event
from app.models.domain import IngestResult
from app.repos.items import ItemRepository
from app.repos.runs import RunRepository
from app.services.source_registry import SourceRegistry


class IngestionService:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        source_registry: SourceRegistry,
        item_repository: ItemRepository,
        run_repository: RunRepository,
    ) -> None:
        self.session_factory = session_factory
        self.source_registry = source_registry
        self.item_repository = item_repository
        self.run_repository = run_repository
        self.logger = get_logger("app.ingestion")

    async def ingest(
        self,
        *,
        sources: list[str] | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
    ) -> IngestResult:
        target_sources = sources or self.source_registry.enabled_sources()
        stats: dict[str, int] = {}
        errors: dict[str, str] = {}
        stored_items = 0

        async with self.session_factory() as session:
            run = await self.run_repository.create(
                session,
                run_type="ingest",
                window_start_utc=from_at,
                window_end_utc=to_at,
            )
            await session.commit()

            try:
                for source_name in target_sources:
                    try:
                        connector = self.source_registry.build(source_name)
                        log_event(self.logger, logging.INFO, "start", run_id=run.id, source=source_name, step="start")
                        items = await connector.fetch(from_at, to_at)
                        stats[source_name] = len(items)
                        log_event(
                            self.logger,
                            logging.INFO,
                            "fetch_done",
                            run_id=run.id,
                            source=source_name,
                            step="fetch_done",
                            item_count=len(items),
                        )
                        max_cursor = None
                        async with self.session_factory() as write_session:
                            for item in items:
                                await self.item_repository.store_fetched_item(write_session, item)
                                stored_items += 1
                                if max_cursor is None or item.published_at_utc > max_cursor:
                                    max_cursor = item.published_at_utc
                            if max_cursor:
                                await self.item_repository.update_checkpoint(
                                    write_session, source_name, max_cursor.isoformat()
                                )
                            await write_session.commit()
                        log_event(
                            self.logger,
                            logging.INFO,
                            "normalize_done",
                            run_id=run.id,
                            source=source_name,
                            step="normalize_done",
                            item_count=len(items),
                        )
                        log_event(self.logger, logging.INFO, "end", run_id=run.id, source=source_name, step="end")
                    except Exception as exc:
                        errors[source_name] = str(exc)
                        log_event(
                            self.logger,
                            logging.ERROR,
                            "source_failed",
                            run_id=run.id,
                            source=source_name,
                            error_code=type(exc).__name__,
                        )
                        continue
                run_status = "failed" if errors and not stats else "succeeded"
                async with self.session_factory() as finish_session:
                    await self.run_repository.finish(
                        finish_session,
                        run.id,
                        status=run_status,
                        stats={"sources": stats, "stored_items": stored_items, "errors": errors},
                    )
                    await finish_session.commit()
                return IngestResult(
                    run_id=run.id,
                    status=run_status,
                    sources=target_sources,
                    stored_items=stored_items,
                    stats={"sources": stats, "errors": errors},
                )
            except Exception as exc:
                async with self.session_factory() as finish_session:
                    await self.run_repository.finish(
                        finish_session,
                        run.id,
                        status="failed",
                        stats={"sources": stats, "stored_items": stored_items},
                        error={"message": str(exc)},
                    )
                    await finish_session.commit()
                log_event(
                    self.logger,
                    logging.ERROR,
                    "ingest_failed",
                    run_id=run.id,
                    error_code=type(exc).__name__,
                )
                raise
