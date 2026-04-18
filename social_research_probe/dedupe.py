"""Duplicate detection using rapidfuzz token_set_ratio."""
from __future__ import annotations

from collections import defaultdict
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
    matches: tuple[str, ...]


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def classify(candidate: str, existing: list[str]) -> DedupeResult:
    """Return DedupeResult comparing candidate to existing entries."""
    if not existing:
        return DedupeResult(DuplicateStatus.NEW, ())

    norm_candidate = _normalize(candidate)
    norm_to_originals: dict[str, list[str]] = defaultdict(list)
    for e in existing:
        norm_to_originals[_normalize(e)].append(e)

    scored = process.extract(
        norm_candidate,
        list(norm_to_originals.keys()),
        scorer=fuzz.token_set_ratio,
        limit=None,
    )

    dup = [orig for name, score, _ in scored if score >= DUPLICATE_THRESHOLD
           for orig in norm_to_originals[name]]
    if dup:
        return DedupeResult(DuplicateStatus.DUPLICATE, tuple(dup))

    near = [orig for name, score, _ in scored if score >= NEAR_DUPLICATE_THRESHOLD
            for orig in norm_to_originals[name]]
    if near:
        return DedupeResult(DuplicateStatus.NEAR_DUPLICATE, tuple(near))

    return DedupeResult(DuplicateStatus.NEW, ())
