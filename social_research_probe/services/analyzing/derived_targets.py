"""Derive binary / multinomial / count / event-time targets from scored items.

Many model families (logistic, Poisson, survival, classification) need a
specific target variable shape. The scored-items list carries everything
we need to construct those targets without extra data capture.

Targets exposed:

- ``is_top_n``: binary — 1 if rank < 5 else 0
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
_TOP_N_CUTOFF = 5


def _score(items: list[dict], field: str) -> list[float]:
    return [float(d.get(field, 0.0)) for d in items]


def _feature(items: list[dict], field: str) -> list[float]:
    return [float((d.get("features") or {}).get(field, 0.0)) for d in items]


def _ranks(items: list[dict]) -> list[int]:
    return list(range(len(items)))


def _top_tenth_cutoff(n: int) -> int:
    return max(2, n // 10)


def _binary(ranks: list[int], cutoff: int) -> list[int]:
    return [1 if r < cutoff else 0 for r in ranks]


def _views(velocity: list[float], age: list[float]) -> list[float]:
    return [v * a for v, a in zip(velocity, age, strict=True)]


def _event_crossed(views: list[float], threshold: float) -> list[int]:
    return [1 if v >= threshold else 0 for v in views]


def _source_class(items: list[dict]) -> list[str]:
    return [str(d.get("source_class", "unknown")) for d in items]


def build_targets(scored_items: list[dict]) -> dict[str, list]:
    """Return a dict of column-aligned target arrays for downstream models."""
    ranks = _ranks(scored_items)
    velocity = _feature(scored_items, "view_velocity")
    engagement = _feature(scored_items, "engagement_ratio")
    age = _feature(scored_items, "age_days")
    views = _views(velocity, age)
    return {
        "rank": [float(r) for r in ranks],
        "is_top_n": _binary(ranks, _TOP_N_CUTOFF),
        "is_top_tenth": _binary(ranks, _top_tenth_cutoff(len(scored_items))),
        "overall": _score(scored_items, "overall_score"),
        "trust": _score(scored_items, "trust"),
        "trend": _score(scored_items, "trend"),
        "opportunity": _score(scored_items, "opportunity"),
        "view_velocity": velocity,
        "engagement_ratio": engagement,
        "age_days": age,
        "subscribers": _feature(scored_items, "subscriber_count"),
        "views": views,
        "source_class": _source_class(scored_items),
        "event_crossed_100k": _event_crossed(views, _VIEW_EVENT_THRESHOLD),
        "time_to_event_days": age,
    }
