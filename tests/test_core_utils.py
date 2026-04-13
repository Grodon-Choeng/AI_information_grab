from __future__ import annotations

from datetime import UTC, datetime

from app.core.hashing import stable_hash
from app.core.similarity import title_similarity, token_overlap_ratio
from app.core.time import business_date
from app.core.urls import normalize_url


def test_normalize_url_strips_tracking_params() -> None:
    url = "https://Example.com/path/?utm_source=test&a=1&fbclid=abc"
    assert normalize_url(url) == "https://example.com/path?a=1"


def test_business_date_uses_shanghai_boundary() -> None:
    value = datetime(2026, 4, 13, 16, 30, tzinfo=UTC)
    assert business_date(value, "Asia/Shanghai").isoformat() == "2026-04-14"


def test_title_similarity_handles_near_duplicates() -> None:
    left = "OpenAI releases new agent SDK for enterprise workflows"
    right = "OpenAI released a new agent SDK for enterprise workflow automation"
    assert title_similarity(left, right) > 0.7
    assert token_overlap_ratio(left, right) > 0.5


def test_hash_is_stable_case_insensitive() -> None:
    assert stable_hash("Hello") == stable_hash("hello")
