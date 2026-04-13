from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

from app.models.domain import FetchedItem


class BaseConnector(ABC):
    source_name: str

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    def checkpoint_key(self) -> str:
        return self.source_name

    @abstractmethod
    async def fetch(self, window_start_utc: datetime | None, window_end_utc: datetime | None) -> list[FetchedItem]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_item: dict[str, Any]) -> FetchedItem:
        raise NotImplementedError

    def build_client(self, *, base_url: str | None = None, headers: dict[str, str] | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=30.0,
            transport=self.transport,
        )
