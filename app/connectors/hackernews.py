from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.base import BaseConnector
from app.core.settings import HackerNewsSourceConfig
from app.models.domain import FetchedItem


class HackerNewsConnector(BaseConnector):
    source_name = "hackernews"

    def __init__(self, config: HackerNewsSourceConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config = config

    async def fetch(self, window_start_utc: datetime | None, window_end_utc: datetime | None) -> list[FetchedItem]:
        results: list[FetchedItem] = []
        async with self.build_client(base_url="https://hn.algolia.com") as client:
            for query in self.config.queries:
                response = await client.get(
                    "/api/v1/search_by_date",
                    params={"query": query, "tags": "story", "hitsPerPage": self.config.limit},
                )
                response.raise_for_status()
                for hit in response.json().get("hits", []):
                    hit["query_term"] = query
                    fetched = self.normalize(hit)
                    if self._within_window(fetched.published_at_utc, window_start_utc, window_end_utc):
                        results.append(fetched)
        return results

    def normalize(self, raw_item: dict[str, Any]) -> FetchedItem:
        published_at = datetime.fromisoformat(raw_item["created_at"].replace("Z", "+00:00")).astimezone(UTC)
        item_url = raw_item.get("url") or f"https://news.ycombinator.com/item?id={raw_item['objectID']}"
        return FetchedItem(
            source=self.source_name,
            source_item_id=raw_item["objectID"],
            title=raw_item.get("title") or raw_item.get("story_title") or "",
            url=item_url,
            author=raw_item.get("author"),
            content_text=raw_item.get("story_text"),
            published_at_utc=published_at,
            source_score=float(raw_item.get("points", 0) + raw_item.get("num_comments", 0)),
            topic_hint=raw_item.get("query_term"),
            payload=raw_item,
        )

    @staticmethod
    def _within_window(
        published_at_utc: datetime,
        window_start_utc: datetime | None,
        window_end_utc: datetime | None,
    ) -> bool:
        if window_start_utc and published_at_utc < window_start_utc:
            return False
        if window_end_utc and published_at_utc >= window_end_utc:
            return False
        return True
