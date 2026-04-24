"""Detect packet-level warnings about result quality.

The pipeline previously hard-coded ``warnings=[]``, which always rendered as
"_(none)_" even when results had real quality concerns (low channel
diversity, no corroboration, low absolute scores, stale content). This
module inspects the fetched items, derived signals, and scored top-N to
return a list of human-readable warnings the user should consider before
acting on the report.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime

from social_research_probe.platforms.base import RawItem, SignalSet
from social_research_probe.utils.core.types import ScoredItem

_LOW_CHANNEL_THRESHOLD = 3
_LOW_SCORE_THRESHOLD = 0.5
_STALE_AGE_DAYS = 30
_SPARSE_FETCH_THRESHOLD = 3


def detect(
    items: list[RawItem],
    signals: list[SignalSet],
    top_n: list[ScoredItem],
    now: datetime | None = None,
    corroboration_ran: bool = False,
    corroboration_skip_reason: str | None = None,
) -> list[str]:
    """Return a list of warning strings about quality concerns.

    Includes a corroboration reminder only when the pipeline skipped the
    corroboration stage, so users do not mistake the heuristic trust score for
    a verified source check. Pass ``corroboration_skip_reason`` to make the
    HTML report self-explanatory (e.g. "backend disabled in config").
    """
    reference_now = now or datetime.now(UTC)
    notes: list[str] = []
    _check_fetch_volume(items, notes)
    _check_channel_diversity(items, notes)
    _check_top_n_quality(top_n, notes)
    _check_freshness(signals, reference_now, notes)
    if not corroboration_ran:
        suffix = f" ({corroboration_skip_reason})" if corroboration_skip_reason else ""
        notes.append(f"source corroboration was not run{suffix}; trust scores are heuristic only")
    return notes


def _check_fetch_volume(items: list[RawItem], notes: list[str]) -> None:
    if not items:
        notes.append("no items fetched from platform")
        return
    if len(items) < _SPARSE_FETCH_THRESHOLD:
        notes.append(
            f"sparse fetch: only {len(items)} items returned (threshold {_SPARSE_FETCH_THRESHOLD})"
        )


def _check_channel_diversity(items: list[RawItem], notes: list[str]) -> None:
    unique = len({it.author_name for it in items if it.author_name})
    if 0 < unique < _LOW_CHANNEL_THRESHOLD:
        notes.append(f"low channel diversity: only {unique} unique channels")


def _check_top_n_quality(top_n: list[ScoredItem], notes: list[str]) -> None:
    if not top_n:
        return
    if all(d.get("source_class") == "commentary" for d in top_n):
        notes.append("all top-N items are commentary; no primary or secondary sources")
    if all(d.get("source_class") == "unknown" for d in top_n):
        notes.append("all top-N items have unknown source classification")
    if all(d.get("scores", {}).get("overall", 0.0) < _LOW_SCORE_THRESHOLD for d in top_n):
        notes.append(f"all top-N items scored below {_LOW_SCORE_THRESHOLD}")


def _check_freshness(signals: list[SignalSet], now: datetime, notes: list[str]) -> None:
    ages = [max(0.0, (now - s.upload_date).days) for s in signals if s.upload_date]
    if not ages:
        return
    median_age = statistics.median(ages)
    if median_age > _STALE_AGE_DAYS:
        notes.append(
            f"stale content: median upload age is {median_age:.0f}d (threshold {_STALE_AGE_DAYS}d)"
        )
