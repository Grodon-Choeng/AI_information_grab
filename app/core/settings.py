from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DedupConfig(BaseModel):
    title_similarity_threshold: float = 0.84
    max_cluster_window_hours: int = 36
    min_token_overlap: float = 0.5


class LLMConfig(BaseModel):
    enabled: bool = True
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b-instruct"
    timeout_seconds: int = 30


class GitHubSourceConfig(BaseModel):
    enabled: bool = True
    per_page: int = 20
    queries: list[str] = Field(default_factory=list)
    watch_repositories: list[str] = Field(default_factory=list)


class RedditSourceConfig(BaseModel):
    enabled: bool = True
    limit: int = 20
    subreddits: list[str] = Field(default_factory=list)
    sorts: list[str] = Field(default_factory=lambda: ["new"])


class HackerNewsSourceConfig(BaseModel):
    enabled: bool = True
    limit: int = 20
    queries: list[str] = Field(default_factory=list)


class SourcesConfig(BaseModel):
    github: GitHubSourceConfig = Field(default_factory=GitHubSourceConfig)
    reddit: RedditSourceConfig = Field(default_factory=RedditSourceConfig)
    hackernews: HackerNewsSourceConfig = Field(default_factory=HackerNewsSourceConfig)


class SourceConfigFile(BaseModel):
    timezone: str = "Asia/Shanghai"
    dedup: DedupConfig = Field(default_factory=DedupConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)


class EnvironmentSettings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_information_grab"
    timezone: str = "Asia/Shanghai"
    config_path: str = "config/sources.yaml"
    github_token: str | None = None
    reddit_user_agent: str = "ai-information-grab/0.1.0"
    llm_enabled: bool = True
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_environment_settings() -> EnvironmentSettings:
    return EnvironmentSettings()


@lru_cache
def load_source_config(config_path: str | None = None) -> SourceConfigFile:
    env = get_environment_settings()
    raw_path = Path(config_path or env.config_path)
    data = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
    config = SourceConfigFile.model_validate(data)
    if env.timezone:
        config.timezone = env.timezone
    config.llm.enabled = env.llm_enabled and config.llm.enabled
    config.llm.base_url = env.llm_base_url or config.llm.base_url
    config.llm.model = env.llm_model or config.llm.model
    config.llm.timeout_seconds = env.llm_timeout_seconds or config.llm.timeout_seconds
    return config
