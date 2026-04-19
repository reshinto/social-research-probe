"""Derive binary / multinomial / count / event-time targets from scored items.

Many model families (logistic, Poisson, survival, classification) need a
specific target variable shape. The scored-items list carries everything
we need to construct those targets without extra data capture.

Targets exposed:

- ``is_top_5``: binary — 1 if rank < 5 else 0
- ``is_top_tenth``: binary — 1 if rank < n/10 else 0 (for larger n)
- ``rank``: ordinal — index in the sorted list
- ``overall``: continuous — the raw ranking score
- ``source_class``: categorical — primary/secondary/commentary/unknown
- ``views``: count — raw YouTube view count (via features/extras)
- ``event_crossed_100k``: binary — 1 if views >= 100_000 else 0
- ``age_days``: continuous — days since upload (from features)
"""

from __future__ import annotations

_VIEW_EVENT_THRESHOLD = 100_000


def build_targets(scored_items: list[dict]) -> dict[str, list]:
    """Return a dict of column-aligned target arrays for downstream models."""
    n = len(scored_items)
    top5_cutoff = 5
    top_tenth_cutoff = max(2, n // 10)
    ranks = list(range(n))
    overall = [d["scores"]["overall"] for d in scored_items]
    trust = [d["scores"]["trust"] for d in scored_items]
    trend = [d["scores"]["trend"] for d in scored_items]
    opportunity = [d["scores"]["opportunity"] for d in scored_items]
    view_velocity = [d["features"]["view_velocity"] for d in scored_items]
    engagement_ratio = [d["features"]["engagement_ratio"] for d in scored_items]
    age_days = [d["features"]["age_days"] for d in scored_items]
    subscribers = [d["features"]["subscriber_count"] for d in scored_items]
    views = [vel * age for vel, age in zip(view_velocity, age_days, strict=True)]
    source_class = [d.get("source_class", "unknown") for d in scored_items]
    is_top_5 = [1 if r < top5_cutoff else 0 for r in ranks]
    is_top_tenth = [1 if r < top_tenth_cutoff else 0 for r in ranks]
    event_crossed = [1 if v >= _VIEW_EVENT_THRESHOLD else 0 for v in views]
    return {
        "rank": [float(r) for r in ranks],
        "is_top_5": is_top_5,
        "is_top_tenth": is_top_tenth,
        "overall": overall,
        "trust": trust,
        "trend": trend,
        "opportunity": opportunity,
        "view_velocity": view_velocity,
        "engagement_ratio": engagement_ratio,
        "age_days": age_days,
        "subscribers": subscribers,
        "views": views,
        "source_class": source_class,
        "event_crossed_100k": event_crossed,
        "time_to_event_days": age_days,
    }
