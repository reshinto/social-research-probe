"""Dataset key computation for cache namespacing."""

from __future__ import annotations

import json

from social_research_probe.utils.caching.pipeline_cache import hash_key

_ROUND_DIGITS = 6


def _fingerprint(item: dict) -> dict:
    """Document the fingerprint rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _fingerprint(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            {"enabled": True}
    """
    scores = item.get("scores") or {}
    return {
        "id": item.get("id"),
        "overall": round(float(scores.get("overall", 0.0)), _ROUND_DIGITS),
        "trust": round(float(scores.get("trust", 0.0)), _ROUND_DIGITS),
        "trend": round(float(scores.get("trend", 0.0)), _ROUND_DIGITS),
        "opportunity": round(float(scores.get("opportunity", 0.0)), _ROUND_DIGITS),
    }


def dataset_key(items: list[dict], *, namespace: str) -> str:
    """Return a deterministic cache key for ``items`` under ``namespace``.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        items: Ordered source items being carried through the current pipeline step.
        namespace: Metric namespace used to choose the matching field group.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            dataset_key(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                namespace="youtube",
            )
        Output:
            "AI safety"
    """
    serialised = json.dumps([_fingerprint(d) for d in items], sort_keys=True)
    return hash_key(namespace, serialised)
