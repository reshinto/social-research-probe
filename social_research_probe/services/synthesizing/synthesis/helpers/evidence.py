"""Evidence aggregator — narrates what the fetched items collectively show.

``run_research`` hands raw items, computed engagement_metrics, and the scored top-N list
to ``summarize()`` and receives a single human-readable sentence that
captures channel diversity, freshness, engagement, and source-class mix.
The pipeline stores this as ``report["evidence_summary"]`` so downstream
consumers (skill output, rendered reports) see real narrative instead of a
placeholder string.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime

from social_research_probe.utils.core.types import EngagementMetrics, RawItem, ScoredItem


def summarize(
    items: list[RawItem],
    engagement_metrics: list[EngagementMetrics],
    top_n: list[ScoredItem],
    now: datetime | None = None,
) -> str:
    """Build an evidence sentence from fetched items, engagement_metrics, and scored top-N.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.
        top_n: Ordered source items being carried through the current pipeline step.
        now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            summarize(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                engagement_metrics={"views": 1200, "likes": 80},
                top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
                now=datetime(2026, 1, 1),
            )
        Output:
            "AI safety"
    """
    if not items:
        return "no items fetched"

    reference_now = now or datetime.now(UTC)
    parts: list[str] = [f"{len(items)} items from {_unique_channels(items)} channels"]

    median_age = _median_age_days(engagement_metrics, reference_now)
    if median_age is not None:
        parts.append(f"median upload age {median_age:.0f}d")

    velocity = _mean_velocity(engagement_metrics)
    if velocity is not None:
        parts.append(f"avg view velocity {velocity:,.0f}/day")

    engagement = _mean_engagement(engagement_metrics)
    if engagement is not None:
        parts.append(f"avg engagement {engagement:.3f}")

    mix = _source_class_mix(top_n)
    if mix:
        parts.append(f"top-N source mix: {mix}")

    return "; ".join(parts)


def summarize_engagement_metrics(engagement_metrics: list[EngagementMetrics]) -> str:
    """Build a compact metric summary of platform engagement_metrics.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            summarize_engagement_metrics(
                engagement_metrics={"views": 1200, "likes": 80},
            )
        Output:
            "AI safety"
    """
    if not engagement_metrics:
        return "no data"

    parts: list[str] = [f"{len(engagement_metrics)} items"]
    total_views = sum(s.views or 0 for s in engagement_metrics)
    parts.append(f"total views: {total_views:,}")

    velocity = _mean_velocity(engagement_metrics)
    if velocity is not None:
        max_velocity = max(s.view_velocity or 0.0 for s in engagement_metrics)
        parts.append(f"view velocity mean={velocity:,.0f}/day max={max_velocity:,.0f}/day")

    engagement = _mean_engagement(engagement_metrics)
    if engagement is not None:
        parts.append(f"engagement ratio mean={engagement:.3f}")

    return "; ".join(parts)


def _author_name_of(item: object) -> str:
    """Calculate author name of for evidence and engagement summaries.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _author_name_of(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            "AI safety"
    """
    if isinstance(item, dict):
        return str(item.get("author_name") or item.get("channel") or "")
    return str(getattr(item, "author_name", "") or "")


def _unique_channels(items: list) -> int:
    """Calculate unique channels for evidence and engagement summaries.

    Services turn platform items into adapter requests and normalize results so stages handle
    success, skip, and failure the same way.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            _unique_channels(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            5
    """
    return len({name for it in items if (name := _author_name_of(it))})


def _median_age_days(engagement_metrics: list[EngagementMetrics], now: datetime) -> float | None:
    """Calculate median age days for evidence summaries.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.
        now: Timestamp used for recency filtering, age calculations, or persisted audit metadata.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _median_age_days(
                engagement_metrics={"views": 1200, "likes": 80},
                now=datetime(2026, 1, 1),
            )
        Output:
            "AI safety"
    """
    ages = [max(0.0, (now - s.upload_date).days) for s in engagement_metrics if s.upload_date]
    return statistics.median(ages) if ages else None


def _mean_velocity(engagement_metrics: list[EngagementMetrics]) -> float | None:
    """Calculate mean velocity for evidence summaries.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _mean_velocity(
                engagement_metrics={"views": 1200, "likes": 80},
            )
        Output:
            "AI safety"
    """
    values = [s.view_velocity for s in engagement_metrics if s.view_velocity is not None]
    return statistics.mean(values) if values else None


def _mean_engagement(engagement_metrics: list[EngagementMetrics]) -> float | None:
    """Calculate mean engagement for evidence summaries.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        engagement_metrics: Engagement metric dictionary used to build report evidence and warnings.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _mean_engagement(
                engagement_metrics={"views": 1200, "likes": 80},
            )
        Output:
            "AI safety"
    """
    values = [s.engagement_ratio for s in engagement_metrics if s.engagement_ratio is not None]
    return statistics.mean(values) if values else None


def _source_class_mix(top_n: list[ScoredItem]) -> str:
    """Summarize the source-class mix among ranked items.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        top_n: Ordered source items being carried through the current pipeline step.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _source_class_mix(
                top_n=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            "AI safety"
    """
    counts: dict[str, int] = {}
    for d in top_n:
        cls = d.get("source_class", "unknown")
        counts[cls] = counts.get(cls, 0) + 1
    if not counts:
        return ""
    return "/".join(f"{v}{k[0].upper()}" for k, v in sorted(counts.items()))
