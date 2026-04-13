from __future__ import annotations

from datetime import UTC

import httpx
import pytest

from app.connectors.github import GitHubConnector
from app.connectors.hackernews import HackerNewsConnector
from app.connectors.reddit import RedditConnector
from app.core.settings import GitHubSourceConfig, HackerNewsSourceConfig, RedditSourceConfig


@pytest.mark.asyncio
async def test_github_connector_fetches_search_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search/repositories"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": 1,
                        "full_name": "example/agent",
                        "updated_at": "2026-04-13T08:00:00Z",
                        "html_url": "https://github.com/example/agent",
                        "owner": {"login": "example"},
                        "description": "Agent framework",
                        "stargazers_count": 42,
                    }
                ]
            },
        )

    connector = GitHubConnector(
        GitHubSourceConfig(queries=["agent"], watch_repositories=[]),
        transport=httpx.MockTransport(handler),
    )
    items = await connector.fetch(None, None)
    assert len(items) == 1
    assert items[0].source_item_id == "repo:1"


@pytest.mark.asyncio
async def test_reddit_connector_fetches_posts() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {
                    "children": [
                        {
                            "data": {
                                "name": "t3_abc",
                                "title": "New open LLM release",
                                "url_overridden_by_dest": "https://example.com/post",
                                "author": "alice",
                                "selftext": "",
                                "created_utc": 1776067200,
                                "score": 12,
                                "subreddit": "LocalLLaMA",
                            }
                        }
                    ]
                }
            },
        )

    connector = RedditConnector(
        RedditSourceConfig(subreddits=["LocalLLaMA"], sorts=["new"], limit=5),
        transport=httpx.MockTransport(handler),
    )
    items = await connector.fetch(None, None)
    assert len(items) == 1
    assert items[0].published_at_utc.year == 2026


@pytest.mark.asyncio
async def test_hackernews_connector_fetches_hits() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "hits": [
                    {
                        "objectID": "123",
                        "title": "New benchmark for agentic coding",
                        "url": "https://example.com/hn",
                        "author": "bob",
                        "created_at": "2026-04-13T02:00:00Z",
                        "points": 20,
                        "num_comments": 5,
                    }
                ]
            },
        )

    connector = HackerNewsConnector(
        HackerNewsSourceConfig(queries=["agent"], limit=5),
        transport=httpx.MockTransport(handler),
    )
    items = await connector.fetch(None, None)
    assert len(items) == 1
    assert items[0].published_at_utc == items[0].published_at_utc.astimezone(UTC)
