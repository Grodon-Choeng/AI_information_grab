from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.llm import LLMService


class HealthService:
    def __init__(self, session_factory: async_sessionmaker, llm_service: LLMService) -> None:
        self.session_factory = session_factory
        self.llm_service = llm_service

    async def check(self) -> dict[str, object]:
        database_ok = False
        async with self.session_factory() as session:
            try:
                await session.execute(text("SELECT 1"))
                database_ok = True
            except Exception:
                database_ok = False
        llm_ok = await self.llm_service.is_available()
        return {
            "status": "ok" if database_ok else "degraded",
            "database": {"ok": database_ok},
            "llm": {"ok": llm_ok, "enabled": self.llm_service.config.enabled},
            "now_utc": datetime.now(tz=UTC).isoformat(),
        }
