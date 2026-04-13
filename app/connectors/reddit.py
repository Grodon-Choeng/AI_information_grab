from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.base import BaseConnector
from app.core.settings import RedditSourceConfig, get_environment_settings
from app.models.domain import FetchedItem


class RedditConnector(BaseConnector):
    source_name = "reddit"

    def __init__(self, config: RedditSourceConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.env = get_environment_settings()

    async def fetch(self, window_start_utc: datetime | None, window_end_utc: datetime | None) -> list[FetchedItem]:
        headers = {"User-Agent": self.env.reddit_user_agent}
        results: list[FetchedItem] = []
        async with self.build_client(base_url="https://www.reddit.com", headers=headers) as client:
            for subreddit in self.config.subreddits:
                for sort in self.config.sorts:
                    response = await client.get(
                        f"/r/{subreddit}/{sort}.json",
                        params={"limit": self.config.limit},
                    )
                    response.raise_for_status()
                    children = response.json().get("data", {}).get("children", [])
                    for child in children:
                        payload = child.get("data", {})
                        payload["subreddit_sort"] = sort
                        fetched = self.normalize(payload)
                        if self._within_window(fetched.published_at_utc, window_start_utc, window_end_utc):
                            results.append(fetched)
        return results

    def normalize(self, raw_item: dict[str, Any]) -> FetchedItem:
        permalink = raw_item.get("permalink") or ""
        published_at = datetime.fromtimestamp(float(raw_item["created_utc"]), tz=UTC)
        external_url = raw_item.get("url_overridden_by_dest") or raw_item.get("url")
        return FetchedItem(
            source=self.source_name,
            source_item_id=raw_item["name"],
            title=raw_item.get("title") or "",
            url=external_url or f"https://www.reddit.com{permalink}",
            author=raw_item.get("author"),
            content_text=raw_item.get("selftext"),
            published_at_utc=published_at,
            source_score=float(raw_item.get("score", 0)),
            topic_hint=raw_item.get("subreddit"),
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
