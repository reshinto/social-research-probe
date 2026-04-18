"""Duplicate detection using rapidfuzz token_set_ratio."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz, process

DUPLICATE_THRESHOLD = 95
NEAR_DUPLICATE_THRESHOLD = 80


class DuplicateStatus(str, Enum):
    NEW = "new"
    NEAR_DUPLICATE = "near-duplicate"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class DedupeResult:
    status: DuplicateStatus
    matches: list[str]


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def classify(candidate: str, existing: list[str]) -> DedupeResult:
    """Return DedupeResult comparing candidate to existing entries."""
    if not existing:
        return DedupeResult(DuplicateStatus.NEW, [])

    norm_candidate = _normalize(candidate)
    normalized = {_normalize(e): e for e in existing}

    scored = process.extract(
        norm_candidate,
        list(normalized.keys()),
        scorer=fuzz.token_set_ratio,
        limit=len(normalized),
    )

    dup = [normalized[name] for name, score, _ in scored if score >= DUPLICATE_THRESHOLD]
    if dup:
        return DedupeResult(DuplicateStatus.DUPLICATE, dup)

    near = [normalized[name] for name, score, _ in scored if score >= NEAR_DUPLICATE_THRESHOLD]
    if near:
        return DedupeResult(DuplicateStatus.NEAR_DUPLICATE, near)

    return DedupeResult(DuplicateStatus.NEW, [])
