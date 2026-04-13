from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any


@dataclass(slots=True)
class FetchedItem:
    source: str
    source_item_id: str
    title: str
    url: str | None
    published_at_utc: datetime
    payload: dict[str, Any]
    author: str | None = None
    content_text: str | None = None
    source_score: float = 0.0
    topic_hint: str | None = None

    def __post_init__(self) -> None:
        if self.published_at_utc.tzinfo is None:
            self.published_at_utc = self.published_at_utc.replace(tzinfo=UTC)
        else:
            self.published_at_utc = self.published_at_utc.astimezone(UTC)


@dataclass(slots=True)
class IngestResult:
    run_id: str
    status: str
    sources: list[str]
    stored_items: int
    stats: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DigestEntry:
    cluster_id: str
    title: str
    url: str | None
    summary: str
    topic: str
    importance_score: float
    sources: list[str]


@dataclass(slots=True)
class DigestResult:
    run_id: str
    biz_date: date
    cluster_count: int
    llm_used: bool
    entries: list[DigestEntry] = field(default_factory=list)
