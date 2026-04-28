"""Dataset key computation for cache namespacing."""

from __future__ import annotations

import json

from social_research_probe.utils.caching.pipeline_cache import hash_key

_ROUND_DIGITS = 6


def _fingerprint(item: dict) -> dict:
    scores = item.get("scores") or {}
    return {
        "id": item.get("id"),
        "overall": round(float(scores.get("overall", 0.0)), _ROUND_DIGITS),
        "trust": round(float(scores.get("trust", 0.0)), _ROUND_DIGITS),
        "trend": round(float(scores.get("trend", 0.0)), _ROUND_DIGITS),
        "opportunity": round(float(scores.get("opportunity", 0.0)), _ROUND_DIGITS),
    }


def dataset_key(items: list[dict], *, namespace: str) -> str:
    """Return a deterministic cache key for ``items`` under ``namespace``."""
    serialised = json.dumps([_fingerprint(d) for d in items], sort_keys=True)
    return hash_key(namespace, serialised)
