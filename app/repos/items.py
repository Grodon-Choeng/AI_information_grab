from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import stable_hash
from app.core.time import business_date
from app.core.urls import normalize_url
from app.models.domain import FetchedItem
from app.models.orm import CanonicalCluster, ClusterMember, DailyDigest, NormalizedItem, RawItem, SourceCheckpoint


class ItemRepository:
    def __init__(self, timezone_name: str) -> None:
        self.timezone_name = timezone_name

    async def store_fetched_item(self, session: AsyncSession, item: FetchedItem) -> tuple[RawItem, NormalizedItem]:
        raw_item = await session.scalar(
            select(RawItem).where(
                RawItem.source == item.source,
                RawItem.source_item_id == item.source_item_id,
            )
        )
        if raw_item is None:
            raw_item = RawItem(
                source=item.source,
                source_item_id=item.source_item_id,
                fetched_at_utc=datetime.now(tz=UTC),
                payload_json=item.payload,
            )
            session.add(raw_item)
            await session.flush()
        else:
            raw_item.payload_json = item.payload
            raw_item.fetched_at_utc = datetime.now(tz=UTC)

        normalized_url = normalize_url(item.url)
        normalized_item = await session.scalar(
            select(NormalizedItem).where(
                NormalizedItem.source == item.source,
                NormalizedItem.source_item_id == item.source_item_id,
            )
        )
        payload = {
            "raw_item_id": raw_item.id,
            "source": item.source,
            "source_item_id": item.source_item_id,
            "title": item.title,
            "author": item.author,
            "url": item.url,
            "normalized_url": normalized_url or None,
            "url_hash": stable_hash(normalized_url) if normalized_url else "",
            "title_hash": stable_hash(item.title),
            "content_text": item.content_text,
            "published_at_utc": item.published_at_utc,
            "biz_date": business_date(item.published_at_utc, self.timezone_name),
            "source_score": item.source_score,
            "topic_hint": item.topic_hint,
        }
        if normalized_item is None:
            normalized_item = NormalizedItem(**payload)
            session.add(normalized_item)
        else:
            for key, value in payload.items():
                setattr(normalized_item, key, value)
        await session.flush()
        return raw_item, normalized_item

    async def update_checkpoint(self, session: AsyncSession, source: str, cursor_value: str) -> None:
        checkpoint = await session.get(SourceCheckpoint, source)
        if checkpoint is None:
            checkpoint = SourceCheckpoint(source=source, cursor_kind="published_at", cursor_value=cursor_value)
            session.add(checkpoint)
        else:
            checkpoint.cursor_kind = "published_at"
            checkpoint.cursor_value = cursor_value
            checkpoint.updated_at_utc = datetime.now(tz=UTC)
        await session.flush()

    async def list_items(
        self,
        session: AsyncSession,
        *,
        biz_date: date | None = None,
        source: str | None = None,
        topic: str | None = None,
        dedup_status: str | None = None,
        canonical_only: bool = False,
    ) -> list[NormalizedItem]:
        stmt = select(NormalizedItem).order_by(NormalizedItem.published_at_utc.desc())
        if biz_date is not None:
            stmt = stmt.where(NormalizedItem.biz_date == biz_date)
        if source:
            stmt = stmt.where(NormalizedItem.source == source)
        if topic:
            stmt = stmt.where(NormalizedItem.topic_hint == topic)
        if dedup_status:
            stmt = stmt.where(NormalizedItem.dedup_status == dedup_status)
        if canonical_only:
            stmt = stmt.where(NormalizedItem.dedup_status == "canonical")
        result = await session.scalars(stmt)
        return list(result)

    async def list_items_for_date(self, session: AsyncSession, biz_date: date) -> list[NormalizedItem]:
        result = await session.scalars(
            select(NormalizedItem)
            .where(NormalizedItem.biz_date == biz_date)
            .order_by(NormalizedItem.source_score.desc(), NormalizedItem.published_at_utc.desc())
        )
        return list(result)

    async def replace_clusters_for_date(
        self,
        session: AsyncSession,
        *,
        biz_date: date,
        clusters: Iterable[CanonicalCluster],
        memberships: Iterable[ClusterMember],
        digest: DailyDigest,
        statuses: dict[str, tuple[str, str | None]],
    ) -> DailyDigest:
        existing_clusters = await session.scalars(
            select(CanonicalCluster.id).where(CanonicalCluster.biz_date == biz_date)
        )
        existing_cluster_ids = list(existing_clusters)
        items = await self.list_items_for_date(session, biz_date)
        for item in items:
            item.cluster_id = None
            item.dedup_status = "unprocessed"
        await session.flush()
        if existing_cluster_ids:
            await session.execute(delete(ClusterMember).where(ClusterMember.cluster_id.in_(existing_cluster_ids)))
            await session.execute(delete(CanonicalCluster).where(CanonicalCluster.id.in_(existing_cluster_ids)))
        await session.execute(delete(DailyDigest).where(DailyDigest.biz_date == biz_date))

        for cluster in clusters:
            session.add(cluster)
        await session.flush()
        for membership in memberships:
            session.add(membership)
        for item in items:
            status, cluster_id = statuses.get(item.id, ("unprocessed", None))
            item.dedup_status = status
            item.cluster_id = cluster_id
        session.add(digest)
        await session.flush()
        return digest

    async def get_digest_by_date(self, session: AsyncSession, biz_date: date) -> DailyDigest | None:
        return await session.scalar(select(DailyDigest).where(DailyDigest.biz_date == biz_date))
