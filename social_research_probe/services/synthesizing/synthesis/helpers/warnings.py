"""Detect report-level warnings about result quality."""

from __future__ import annotations

import statistics
from datetime import UTC, datetime

from social_research_probe.utils.core.types import EngagementMetrics, RawItem, ScoredItem

_LOW_CHANNEL_THRESHOLD = 3
_LOW_SCORE_THRESHOLD = 0.5
_STALE_AGE_DAYS = 30
_SPARSE_FETCH_THRESHOLD = 3


def detect(
    items: list[RawItem],
    engagement_metrics: list[EngagementMetrics],
    top_n: list[ScoredItem],
    now: datetime | None = None,
    corroboration_ran: bool = False,
    corroboration_skip_reason: str | None = None,
) -> list[str]:
    """Return a list of warning strings about quality concerns.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.
        top_n: Ordered source items being carried through the current pipeline step.
        now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.
        corroboration_ran: Flag that selects the branch for this operation.
                corroboration_skip_reason: Reason the corroboration stage was skipped, if any.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            detect(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                engagement_metrics={"views": 1200, "likes": 80},
                top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                now=datetime(2026, 1, 1),
                corroboration_ran=True,
                corroboration_skip_reason="AI safety",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    reference_now = now or datetime.now(UTC)
    notes: list[str] = []
    _check_fetch_volume(items, notes)
    _check_channel_diversity(items, notes)
    _check_top_n_quality(top_n, notes)
    _check_freshness(engagement_metrics, reference_now, notes)
    if not corroboration_ran:
        suffix = f" ({corroboration_skip_reason})" if corroboration_skip_reason else ""
        notes.append(f"source corroboration was not run{suffix}; trust scores are heuristic only")
    return notes


def _check_fetch_volume(items: list[RawItem], notes: list[str]) -> None:
    """Append a warning when fetch volume makes the report less reliable.

    Warnings are collected centrally so the final report can explain data limitations consistently.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        notes: Warning or penalty records that explain reduced evidence quality.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _check_fetch_volume(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                notes=["Transcript unavailable"],
            )
        Output:
            None
    """
    if not items:
        notes.append("no items fetched from platform")
        return
    if len(items) < _SPARSE_FETCH_THRESHOLD:
        notes.append(
            f"sparse fetch: only {len(items)} items returned (threshold {_SPARSE_FETCH_THRESHOLD})"
        )


def _check_channel_diversity(items: list[RawItem], notes: list[str]) -> None:
    """Append a warning when channel diversity makes the report less reliable.

    Warnings are collected centrally so the final report can explain data limitations consistently.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        notes: Warning or penalty records that explain reduced evidence quality.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _check_channel_diversity(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                notes=["Transcript unavailable"],
            )
        Output:
            None
    """
    unique = len({it.author_name for it in items if it.author_name})
    if 0 < unique < _LOW_CHANNEL_THRESHOLD:
        notes.append(f"low channel diversity: only {unique} unique channels")


def _check_top_n_quality(top_n: list[ScoredItem], notes: list[str]) -> None:
    """Append a warning when top n quality makes the report less reliable.

    Warnings are collected centrally so the final report can explain data limitations consistently.

    Args:
        top_n: Ordered source items being carried through the current pipeline step.
        notes: Warning or penalty records that explain reduced evidence quality.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _check_top_n_quality(
                top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                notes=["Transcript unavailable"],
            )
        Output:
            None
    """
    if not top_n:
        return
    if all(d.get("source_class") == "commentary" for d in top_n):
        notes.append("all top-N items are commentary; no primary or secondary sources")
    if all(d.get("source_class") == "unknown" for d in top_n):
        notes.append("all top-N items have unknown source classification")
    if all(d.get("scores", {}).get("overall", 0.0) < _LOW_SCORE_THRESHOLD for d in top_n):
        notes.append(f"all top-N items scored below {_LOW_SCORE_THRESHOLD}")


def _check_freshness(
    engagement_metrics: list[EngagementMetrics], now: datetime, notes: list[str]
) -> None:
    """Append a warning when freshness makes the report less reliable.

    Warnings are collected centrally so the final report can explain data limitations consistently.

    Args:
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.
        now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.
        notes: Warning or penalty records that explain reduced evidence quality.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _check_freshness(
                engagement_metrics={"views": 1200, "likes": 80},
                now=datetime(2026, 1, 1),
                notes=["Transcript unavailable"],
            )
        Output:
            None
    """
    ages = [max(0.0, (now - s.upload_date).days) for s in engagement_metrics if s.upload_date]
    if not ages:
        return
    median_age = statistics.median(ages)
    if median_age > _STALE_AGE_DAYS:
        notes.append(
            f"stale content: median upload age is {median_age:.0f}d (threshold {_STALE_AGE_DAYS}d)"
        )
