from __future__ import annotations

import re
from difflib import SequenceMatcher


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9\u4e00-\u9fff]+")


def tokenize(text: str) -> set[str]:
    return {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)}


def token_overlap_ratio(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    baseline = min(len(left_tokens), len(right_tokens))
    return len(intersection) / baseline


def title_similarity(left: str, right: str) -> float:
    sequence_score = SequenceMatcher(a=left.lower(), b=right.lower()).ratio()
    overlap = token_overlap_ratio(left, right)
    return (sequence_score + overlap) / 2
