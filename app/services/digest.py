from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.hashing import stable_hash
from app.core.logging import get_logger, log_event
from app.core.settings import DedupConfig
from app.core.similarity import title_similarity, token_overlap_ratio
from app.models.domain import DigestEntry, DigestResult
from app.models.orm import CanonicalCluster, ClusterMember, DailyDigest, NormalizedItem, new_uuid
from app.repos.items import ItemRepository
from app.repos.runs import RunRepository
from app.services.llm import LLMService


@dataclass
class ClusterBucket:
    items: list[NormalizedItem] = field(default_factory=list)

    @property
    def representative(self) -> NormalizedItem:
        return sorted(self.items, key=lambda item: (item.source_score, item.published_at_utc), reverse=True)[0]


class DigestService:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        item_repository: ItemRepository,
        run_repository: RunRepository,
        llm_service: LLMService,
        dedup_config: DedupConfig,
    ) -> None:
        self.session_factory = session_factory
        self.item_repository = item_repository
        self.run_repository = run_repository
        self.llm_service = llm_service
        self.dedup_config = dedup_config
        self.logger = get_logger("app.digest")

    async def digest(self, *, biz_date: date) -> DigestResult:
        async with self.session_factory() as session:
            run = await self.run_repository.create(session, run_type="digest", biz_date=biz_date)
            await session.commit()

        try:
            async with self.session_factory() as session:
                items = await self.item_repository.list_items_for_date(session, biz_date)
            clusters = self._cluster_items(items)
            llm_used = False

            cluster_models: list[CanonicalCluster] = []
            membership_models: list[ClusterMember] = []
            status_map: dict[str, tuple[str, str | None]] = {}
            entries: list[DigestEntry] = []

            for bucket in clusters:
                representative = bucket.representative
                payload = {
                    "titles": [item.title for item in bucket.items],
                    "sources": [item.source for item in bucket.items],
                    "topic_hints": [item.topic_hint for item in bucket.items if item.topic_hint],
                    "source_scores": [item.source_score for item in bucket.items],
                }
                summary, used_summary_llm = await self.llm_service.summarize(payload)
                topic, used_topic_llm = await self.llm_service.classify(payload)
                importance_score, used_score_llm = await self.llm_service.score(payload)
                llm_used = llm_used or used_summary_llm or used_topic_llm or used_score_llm

                cluster_id = new_uuid()
                dedup_key = representative.url_hash or stable_hash(representative.title)
                cluster_models.append(
                    CanonicalCluster(
                        id=cluster_id,
                        biz_date=biz_date,
                        dedup_key=dedup_key,
                        representative_title=representative.title,
                        representative_url=representative.normalized_url or representative.url,
                        summary=summary,
                        topic=topic,
                        importance_score=importance_score,
                        llm_used=used_summary_llm or used_topic_llm or used_score_llm,
                    )
                )
                for item in bucket.items:
                    is_representative = item.id == representative.id
                    membership_models.append(
                        ClusterMember(
                            cluster_id=cluster_id,
                            item_id=item.id,
                            is_representative=is_representative,
                        )
                    )
                    status_map[item.id] = ("canonical" if is_representative else "duplicate", cluster_id)
                entries.append(
                    DigestEntry(
                        cluster_id=cluster_id,
                        title=representative.title,
                        url=representative.normalized_url or representative.url,
                        summary=summary,
                        topic=topic,
                        importance_score=importance_score,
                        sources=sorted({item.source for item in bucket.items}),
                    )
                )

            entries.sort(key=lambda entry: entry.importance_score, reverse=True)
            markdown = self._render_markdown(biz_date, entries)
            digest_model = DailyDigest(
                biz_date=biz_date,
                cluster_count=len(entries),
                summary_markdown=markdown,
                payload_json={
                    "biz_date": biz_date.isoformat(),
                    "entries": [
                        {
                            "cluster_id": entry.cluster_id,
                            "title": entry.title,
                            "url": entry.url,
                            "summary": entry.summary,
                            "topic": entry.topic,
                            "importance_score": entry.importance_score,
                            "sources": entry.sources,
                        }
                        for entry in entries
                    ],
                },
            )

            async with self.session_factory() as session:
                await self.item_repository.replace_clusters_for_date(
                    session,
                    biz_date=biz_date,
                    clusters=cluster_models,
                    memberships=membership_models,
                    digest=digest_model,
                    statuses=status_map,
                )
                await self.run_repository.finish(
                    session,
                    run.id,
                    status="succeeded",
                    stats={"cluster_count": len(entries), "llm_used": llm_used},
                )
                await session.commit()

            log_event(
                self.logger,
                logging.INFO,
                "digest_done",
                run_id=run.id,
                step="digest_done",
                item_count=len(entries),
                llm_used=llm_used,
            )
            return DigestResult(
                run_id=run.id,
                biz_date=biz_date,
                cluster_count=len(entries),
                llm_used=llm_used,
                entries=entries,
            )
        except Exception as exc:
            async with self.session_factory() as session:
                await self.run_repository.finish(
                    session,
                    run.id,
                    status="failed",
                    error={"message": str(exc)},
                )
                await session.commit()
            log_event(self.logger, logging.ERROR, "digest_failed", run_id=run.id, error_code=type(exc).__name__)
            raise

    def _cluster_items(self, items: list[NormalizedItem]) -> list[ClusterBucket]:
        seed_buckets: dict[str, ClusterBucket] = {}
        for item in items:
            key = item.url_hash or item.title_hash or item.id
            seed_buckets.setdefault(key, ClusterBucket()).items.append(item)

        buckets = list(seed_buckets.values())
        merged: list[ClusterBucket] = []
        for bucket in sorted(
            buckets,
            key=lambda current: current.representative.source_score,
            reverse=True,
        ):
            target_bucket = None
            for existing in merged:
                if self._should_merge(existing.representative, bucket.representative):
                    target_bucket = existing
                    break
            if target_bucket is None:
                merged.append(bucket)
            else:
                target_bucket.items.extend(bucket.items)
        return merged

    def _should_merge(self, left: NormalizedItem, right: NormalizedItem) -> bool:
        if left.url_hash and right.url_hash and left.url_hash == right.url_hash:
            return True
        similarity = title_similarity(left.title, right.title)
        overlap = token_overlap_ratio(left.title, right.title)
        time_gap = abs((left.published_at_utc - right.published_at_utc).total_seconds()) / 3600
        return (
            similarity >= self.dedup_config.title_similarity_threshold
            and overlap >= self.dedup_config.min_token_overlap
            and time_gap <= self.dedup_config.max_cluster_window_hours
        )

    @staticmethod
    def _render_markdown(biz_date: date, entries: list[DigestEntry]) -> str:
        lines = [f"# AI Digest {biz_date.isoformat()}", ""]
        for index, entry in enumerate(entries, start=1):
            lines.append(f"## {index}. {entry.title}")
            if entry.url:
                lines.append(f"- URL: {entry.url}")
            lines.append(f"- Topic: {entry.topic}")
            lines.append(f"- Score: {entry.importance_score}")
            lines.append(f"- Sources: {', '.join(entry.sources)}")
            lines.append(f"- Summary: {entry.summary}")
            lines.append("")
        return "\n".join(lines).strip()
