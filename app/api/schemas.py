from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    sources: list[str] | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None


class IngestResponse(BaseModel):
    run_id: str
    status: str
    sources: list[str]
    stored_items: int
    stats: dict[str, Any]


class DigestRequest(BaseModel):
    biz_date: date


class DigestEntryResponse(BaseModel):
    cluster_id: str
    title: str
    url: str | None
    summary: str
    topic: str
    importance_score: float
    sources: list[str]


class DigestResponse(BaseModel):
    run_id: str
    biz_date: date
    cluster_count: int
    llm_used: bool
    entries: list[DigestEntryResponse]


class ItemResponse(BaseModel):
    id: str
    source: str
    source_item_id: str
    title: str
    author: str | None
    url: str | None
    normalized_url: str | None
    published_at_utc: datetime
    biz_date: date
    source_score: float
    topic_hint: str | None
    cluster_id: str | None
    dedup_status: str


class SourceResponse(BaseModel):
    timezone: str
    llm_enabled: bool
    sources: dict[str, Any] = Field(default_factory=dict)
