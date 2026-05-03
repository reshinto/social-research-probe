"""Pure-computation helpers for building derived target arrays from scored items."""

from __future__ import annotations

_TOP_N_CUTOFF = 5
_VIEW_EVENT_THRESHOLD = 100_000


def _score(items: list[dict], field: str) -> list[float]:
    """Compute the score used by ranking or analysis.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        field: Metric or data field read from source items.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _score(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                field="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [float((d.get("scores") or {}).get(field, 0.0)) for d in items]


def _feature(items: list[dict], field: str) -> list[float]:
    """Document the feature rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        field: Metric or data field read from source items.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _feature(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                field="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [float((d.get("features") or {}).get(field, 0.0)) for d in items]


def _ranks(items: list[dict]) -> list[int]:
    """Assign ranks used by nonparametric statistical tests.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _ranks(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return list(range(len(items)))


def _top_tenth_cutoff(n: int) -> int:
    """Document the top tenth cutoff rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        n: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            _top_tenth_cutoff(
                n=3,
            )
        Output:
            5
    """
    return max(2, n // 10)


def _binary(ranks: list[int], cutoff: int) -> list[int]:
    """Document the binary rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        ranks: Rank values used to derive percentile-style target fields.
        cutoff: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _binary(
                ranks=["AI safety"],
                cutoff=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [1 if r < cutoff else 0 for r in ranks]


def _views(velocity: list[float], age: list[float]) -> list[float]:
    """Document the views rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        velocity: Velocity metric used by opportunity and growth targets.
        age: Age in days used by recency-based target calculations.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _views(
                velocity=["AI safety"],
                age=["AI safety"],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [v * a for v, a in zip(velocity, age, strict=True)]


def _event_crossed(views: list[float], threshold: float) -> list[int]:
    """Document the event crossed rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        views: View count used by engagement and target calculations.
        threshold: Numeric score, threshold, prior, or confidence value.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _event_crossed(
                views=["AI safety"],
                threshold=0.75,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [1 if v >= threshold else 0 for v in views]


def _source_class(items: list[dict]) -> list[str]:
    """Document the source class rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _source_class(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    return [str(d.get("source_class", "unknown")) for d in items]


def build_targets(scored_items: list[dict]) -> dict[str, list]:
    """Return a dict of column-aligned target arrays for downstream models.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        scored_items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            build_targets(
                scored_items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    ranks = _ranks(scored_items)
    velocity = _feature(scored_items, "view_velocity")
    engagement = _feature(scored_items, "engagement_ratio")
    age = _feature(scored_items, "age_days")
    views = _views(velocity, age)
    return {
        "rank": [float(r) for r in ranks],
        "is_top_n": _binary(ranks, _TOP_N_CUTOFF),
        "is_top_tenth": _binary(ranks, _top_tenth_cutoff(len(scored_items))),
        "overall": _score(scored_items, "overall"),
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
