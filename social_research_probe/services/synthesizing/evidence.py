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

from social_research_probe.platforms.base import EngagementMetrics, RawItem
from social_research_probe.utils.core.types import ScoredItem


def summarize(
    items: list[RawItem],
    engagement_metrics: list[EngagementMetrics],
    top_n: list[ScoredItem],
    now: datetime | None = None,
) -> str:
    """Build an evidence sentence from fetched items, engagement_metrics, and scored top-N.

    Args:
        items: All raw items returned by the adapter.
        engagement_metrics: Parallel list of derived engagement_metrics (one per item).
        top_n: The scored top-N dicts produced by ``_score_item``.
        now: Override for "now" (used by tests to make ages deterministic).

    Returns:
        A single-line summary such as
        "17 items from 14 channels; median upload age 4d;
         avg view velocity 8,432/day; avg engagement 0.042;
         top-N source mix: 5S".

    Why this exists: the raw adapter output is a firehose; consumers need a
    compact narrative that answers "what did the data actually look like?"
    without forcing them to parse every item.
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

    Used for ``report["platform_engagement_summary"]``. Focuses on raw numbers
    (counts, velocities, engagement) rather than the narrative view from
    :func:`summarize`.
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


def _unique_channels(items: list[RawItem]) -> int:
    return len({it.author_name for it in items if it.author_name})


def _median_age_days(engagement_metrics: list[EngagementMetrics], now: datetime) -> float | None:
    ages = [max(0.0, (now - s.upload_date).days) for s in engagement_metrics if s.upload_date]
    return statistics.median(ages) if ages else None


def _mean_velocity(engagement_metrics: list[EngagementMetrics]) -> float | None:
    values = [s.view_velocity for s in engagement_metrics if s.view_velocity is not None]
    return statistics.mean(values) if values else None


def _mean_engagement(engagement_metrics: list[EngagementMetrics]) -> float | None:
    values = [s.engagement_ratio for s in engagement_metrics if s.engagement_ratio is not None]
    return statistics.mean(values) if values else None


def _source_class_mix(top_n: list[ScoredItem]) -> str:
    counts: dict[str, int] = {}
    for d in top_n:
        cls = d.get("source_class", "unknown")
        counts[cls] = counts.get(cls, 0) + 1
    if not counts:
        return ""
    return "/".join(f"{v}{k[0].upper()}" for k, v in sorted(counts.items()))
