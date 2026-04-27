"""AI-slop detection technology: heuristic quality scoring for LLM text."""

from __future__ import annotations

import re
from typing import ClassVar

from social_research_probe.technologies.base import BaseTechnology

_BOILERPLATE_PHRASES: list[str] = [
    "in conclusion",
    "it is important to note",
    "it's worth noting",
    "as an ai",
    "i cannot",
    "delve",
    "certainly",
    "absolutely",
    "of course",
    "great question",
]


def _boilerplate_signal(text: str) -> float:
    lower = text.lower()
    count = sum(1 for phrase in _BOILERPLATE_PHRASES if phrase in lower)
    return min(1.0, count / 3)


def _trigrams(words: list[str]) -> list[tuple[str, str, str]]:
    return [(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)]


def _repetition_signal(text: str) -> float:
    words = text.lower().split()
    grams = _trigrams(words)
    total = len(grams)
    if total == 0:
        return 0.0
    seen: set[tuple[str, str, str]] = set()
    duplicates = 0
    for gram in grams:
        if gram in seen:
            duplicates += 1
        else:
            seen.add(gram)
    return duplicates / total


def _short_sentence_signal(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) < 2:
        return 0.0
    short_count = sum(1 for s in sentences if len(s.split()) < 6)
    return short_count / len(sentences)


def score(text: str) -> float:
    """Return a slop score in [0.0, 1.0] for the given text; higher = more likely slop."""
    if not text or not text.strip():
        return 0.0
    combined = (
        _boilerplate_signal(text) + _repetition_signal(text) + _short_sentence_signal(text)
    ) / 3
    return max(0.0, min(1.0, combined))


class AISlopDetector(BaseTechnology[str, float]):
    """Technology adapter: score text for AI-slop heuristic signals."""

    name: ClassVar[str] = "ai_slop_detector"
    health_check_key: ClassVar[str] = "ai_slop_detector"
    enabled_config_key: ClassVar[str] = "ai_slop_detector"

    async def _execute(self, data: str) -> float:
        return score(data)
