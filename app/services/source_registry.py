from __future__ import annotations

from app.connectors.github import GitHubConnector
from app.connectors.hackernews import HackerNewsConnector
from app.connectors.reddit import RedditConnector
from app.core.settings import SourceConfigFile


class SourceRegistry:
    def __init__(self, config: SourceConfigFile) -> None:
        self.config = config

    def enabled_sources(self) -> list[str]:
        sources = []
        if self.config.sources.github.enabled:
            sources.append("github")
        if self.config.sources.reddit.enabled:
            sources.append("reddit")
        if self.config.sources.hackernews.enabled:
            sources.append("hackernews")
        return sources

    def build(self, source_name: str):
        if source_name == "github":
            return GitHubConnector(self.config.sources.github)
        if source_name == "reddit":
            return RedditConnector(self.config.sources.reddit)
        if source_name == "hackernews":
            return HackerNewsConnector(self.config.sources.hackernews)
        raise ValueError(f"unsupported source: {source_name}")
