"""Duplicate detection using rapidfuzz token_set_ratio."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from rapidfuzz import fuzz, process

DUPLICATE_THRESHOLD = 95
NEAR_DUPLICATE_THRESHOLD = 80


class DuplicateStatus(StrEnum):
    """Duplicate status type.

    Examples:
        Input:
            DuplicateStatus
        Output:
            DuplicateStatus
    """

    NEW = "new"
    NEAR_DUPLICATE = "near-duplicate"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class DedupeResult:
    """Typed shape for dedupe result data.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            DedupeResult
        Output:
            DedupeResult(status="new", matches=())
    """

    status: DuplicateStatus
    matches: tuple[str, ...]


def _normalize(s: str) -> str:
    """Normalize a value before it is stored or compared.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _normalize(
                s="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    return " ".join(s.strip().lower().split())


def classify(candidate: str, existing: list[str]) -> DedupeResult:
    """Document the classify rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        candidate: Candidate topic or purpose name being compared for duplicates.
        existing: Intermediate collection used to preserve ordering while stage results are merged.

    Returns:
        DedupeResult with the duplicate status and matched existing names.

    Examples:
        Input:
            classify(
                candidate="AI safety",
                existing=[],
            )
        Output:
            DedupeResult(status="new", matches=())
    """
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

    dup = [
        orig
        for name, score, _ in scored
        if score >= DUPLICATE_THRESHOLD
        for orig in norm_to_originals[name]
    ]
    if dup:
        return DedupeResult(DuplicateStatus.DUPLICATE, tuple(dup))

    near = [
        orig
        for name, score, _ in scored
        if score >= NEAR_DUPLICATE_THRESHOLD
        for orig in norm_to_originals[name]
    ]
    if near:
        return DedupeResult(DuplicateStatus.NEAR_DUPLICATE, tuple(near))

    return DedupeResult(DuplicateStatus.NEW, ())
