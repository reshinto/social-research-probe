"""Stable hash key for a scored_items dataset.

Used by analyzer caches (stats, charts) so repeat runs on the same scored
dataset reuse work. Includes id + scored fields so any meaningful change to
the dataset busts the key.
"""

from __future__ import annotations

import json

from social_research_probe.utils.caching.pipeline_cache import hash_key

_ROUND_DIGITS = 6


def _fingerprint(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "overall_score": round(float(item.get("overall_score", 0.0)), _ROUND_DIGITS),
        "trust": round(float(item.get("trust", 0.0)), _ROUND_DIGITS),
        "trend": round(float(item.get("trend", 0.0)), _ROUND_DIGITS),
        "opportunity": round(float(item.get("opportunity", 0.0)), _ROUND_DIGITS),
    }


def dataset_key(items: list[dict], *, namespace: str) -> str:
    """Return a deterministic cache key for ``items`` under ``namespace``."""
    serialised = json.dumps([_fingerprint(d) for d in items], sort_keys=True)
    return hash_key(namespace, serialised)
