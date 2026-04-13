from __future__ import annotations

from hashlib import sha256


def stable_hash(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    return sha256(normalized.encode("utf-8")).hexdigest()
