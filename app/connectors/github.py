from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.base import BaseConnector
from app.core.settings import GitHubSourceConfig, get_environment_settings
from app.models.domain import FetchedItem


class GitHubConnector(BaseConnector):
    source_name = "github"

    def __init__(self, config: GitHubSourceConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.env = get_environment_settings()

    async def fetch(self, window_start_utc: datetime | None, window_end_utc: datetime | None) -> list[FetchedItem]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-information-grab"}
        if self.env.github_token:
            headers["Authorization"] = f"Bearer {self.env.github_token}"

        results: list[FetchedItem] = []
        async with self.build_client(base_url="https://api.github.com", headers=headers) as client:
            for query in self.config.queries:
                response = await client.get(
                    "/search/repositories",
                    params={
                        "q": query,
                        "sort": "updated",
                        "order": "desc",
                        "per_page": self.config.per_page,
                    },
                )
                response.raise_for_status()
                for item in response.json().get("items", []):
                    item["kind"] = "repository"
                    fetched = self.normalize(item)
                    if self._within_window(fetched.published_at_utc, window_start_utc, window_end_utc):
                        results.append(fetched)
            for repo_name in self.config.watch_repositories:
                response = await client.get(f"/repos/{repo_name}/releases/latest")
                if response.status_code >= 400:
                    continue
                release = response.json()
                release["kind"] = "release"
                release["repository_name"] = repo_name
                fetched = self.normalize(release)
                if self._within_window(fetched.published_at_utc, window_start_utc, window_end_utc):
                    results.append(fetched)
        return results

    def normalize(self, raw_item: dict[str, Any]) -> FetchedItem:
        kind = raw_item.get("kind", "repository")
        if kind == "release":
            published_at = datetime.fromisoformat(raw_item["published_at"].replace("Z", "+00:00"))
            repo_name = raw_item.get("repository_name", raw_item.get("name", "unknown"))
            return FetchedItem(
                source=self.source_name,
                source_item_id=f"release:{raw_item['id']}",
                title=f"{repo_name} released {raw_item.get('name') or raw_item.get('tag_name')}",
                url=raw_item.get("html_url"),
                author=(raw_item.get("author") or {}).get("login"),
                content_text=raw_item.get("body"),
                published_at_utc=published_at.astimezone(UTC),
                source_score=float(raw_item.get("reactions", {}).get("total_count", 0)),
                topic_hint="release",
                payload=raw_item,
            )

        published_at = datetime.fromisoformat(raw_item["updated_at"].replace("Z", "+00:00"))
        description = raw_item.get("description") or ""
        return FetchedItem(
            source=self.source_name,
            source_item_id=f"repo:{raw_item['id']}",
            title=raw_item["full_name"],
            url=raw_item.get("html_url"),
            author=(raw_item.get("owner") or {}).get("login"),
            content_text=description,
            published_at_utc=published_at.astimezone(UTC),
            source_score=float(raw_item.get("stargazers_count", 0)),
            topic_hint="repository",
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
