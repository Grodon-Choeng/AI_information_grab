from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class Base(DeclarativeBase):
    pass


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    window_start_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    biz_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    stats_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SourceCheckpoint(Base):
    __tablename__ = "source_checkpoints"

    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    cursor_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="published_at")
    cursor_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RawItem(Base):
    __tablename__ = "raw_items"
    __table_args__ = (UniqueConstraint("source", "source_item_id", name="uq_raw_items_source_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    fetched_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class NormalizedItem(Base):
    __tablename__ = "normalized_items"
    __table_args__ = (UniqueConstraint("source", "source_item_id", name="uq_normalized_items_source_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    raw_item_id: Mapped[str | None] = mapped_column(ForeignKey("raw_items.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    biz_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    topic_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(ForeignKey("canonical_clusters.id"), nullable=True)
    dedup_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unprocessed")


class CanonicalCluster(Base):
    __tablename__ = "canonical_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    biz_date: Mapped[date] = mapped_column(Date, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    representative_title: Mapped[str] = mapped_column(Text, nullable=False)
    representative_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    llm_used: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClusterMember(Base):
    __tablename__ = "cluster_members"
    __table_args__ = (UniqueConstraint("cluster_id", "item_id", name="uq_cluster_members_cluster_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    cluster_id: Mapped[str] = mapped_column(ForeignKey("canonical_clusters.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("normalized_items.id"), nullable=False)
    is_representative: Mapped[bool] = mapped_column(nullable=False, default=False)


class DailyDigest(Base):
    __tablename__ = "daily_digests"
    __table_args__ = (UniqueConstraint("biz_date", name="uq_daily_digests_biz_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    biz_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    cluster_count: Mapped[int] = mapped_column(nullable=False, default=0)
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
