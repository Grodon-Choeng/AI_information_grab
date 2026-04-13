from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.logging import log_event
from app.core.settings import LLMConfig


class LLMService:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.logger = logging.getLogger("app.llm")

    async def is_available(self) -> bool:
        if not self.config.enabled:
            return False
        try:
            async with httpx.AsyncClient(base_url=self.config.base_url, timeout=self.config.timeout_seconds) as client:
                response = await client.get("/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def summarize(self, cluster_payload: dict[str, Any]) -> tuple[str, bool]:
        if not self.config.enabled:
            return self._fallback_summary(cluster_payload), False
        prompt = (
            "You are summarizing AI news clusters. Write a concise Chinese summary with 2 sentences. "
            f"Cluster payload: {cluster_payload}"
        )
        try:
            response = await self._generate(prompt)
            return response.strip(), True
        except httpx.HTTPError as exc:
            log_event(self.logger, logging.WARNING, "llm_summary_failed", error=str(exc))
            return self._fallback_summary(cluster_payload), False

    async def classify(self, cluster_payload: dict[str, Any]) -> tuple[str, bool]:
        if not self.config.enabled:
            return self._fallback_topic(cluster_payload), False
        prompt = (
            "Classify this AI news cluster into one short lowercase label such as "
            "research, model-release, tooling, product, funding, benchmark, infrastructure. "
            f"Cluster payload: {cluster_payload}"
        )
        try:
            response = await self._generate(prompt)
            return response.strip().splitlines()[0][:64], True
        except httpx.HTTPError as exc:
            log_event(self.logger, logging.WARNING, "llm_classify_failed", error=str(exc))
            return self._fallback_topic(cluster_payload), False

    async def score(self, cluster_payload: dict[str, Any]) -> tuple[float, bool]:
        if not self.config.enabled:
            return self._fallback_score(cluster_payload), False
        prompt = (
            "Score this AI news cluster from 1 to 10 based on importance for a technical AI watcher. "
            "Return only the number. "
            f"Cluster payload: {cluster_payload}"
        )
        try:
            response = await self._generate(prompt)
            return max(1.0, min(10.0, float(response.strip().split()[0]))), True
        except (httpx.HTTPError, ValueError) as exc:
            log_event(self.logger, logging.WARNING, "llm_score_failed", error=str(exc))
            return self._fallback_score(cluster_payload), False

    async def _generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(base_url=self.config.base_url, timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                "/api/generate",
                json={"model": self.config.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["response"]

    @staticmethod
    def _fallback_summary(cluster_payload: dict[str, Any]) -> str:
        titles = cluster_payload.get("titles", [])
        sources = cluster_payload.get("sources", [])
        if not titles:
            return "本地规则降级摘要：该事件暂无可用标题。"
        top_titles = "；".join(titles[:2])
        return f"本地规则降级摘要：{top_titles}。来源包括 {', '.join(sorted(set(sources)))}。"

    @staticmethod
    def _fallback_topic(cluster_payload: dict[str, Any]) -> str:
        hints = [hint for hint in cluster_payload.get("topic_hints", []) if hint]
        return hints[0].lower() if hints else "ai-news"

    @staticmethod
    def _fallback_score(cluster_payload: dict[str, Any]) -> float:
        source_score = sum(cluster_payload.get("source_scores", []))
        return max(1.0, min(10.0, round(source_score / 50.0 + len(cluster_payload.get("titles", [])), 2)))
