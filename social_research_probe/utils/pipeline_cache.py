"""Pipeline-wide caching helpers built on FilesystemCache.

Wires FilesystemCache into the expensive repeat-work paths (transcripts,
LLM summaries, corroboration lookups) with domain-specific TTLs so repeat
runs on the same topics pay near-zero LLM and subprocess cost.

Cache root is taken from ``SRP_DATA_DIR`` (set by the orchestrator) so each
data directory has its own isolated cache. Caching is bypassed when
``SRP_DISABLE_CACHE=1`` (useful for benchmarking or forcing a refresh).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from social_research_probe.utils.cache import FilesystemCache

_DISABLE_ENV = "SRP_DISABLE_CACHE"
_TRUTHY = {"1", "true", "yes", "on"}

# TTLs tuned to the volatility of each cache domain. Transcripts are
# effectively immutable once captured; summaries depend on the prompt so their
# key already pins the inputs; corroboration is time-sensitive.
TTL_TRANSCRIPT = 7 * 24 * 3600
TTL_WHISPER = 30 * 24 * 3600
TTL_SUMMARY = 7 * 24 * 3600
TTL_CORROBORATION = 6 * 3600
_STAGE_TTLS = {
    "fetch": 6 * 3600,
    "score": 24 * 3600,
    "enrich": 24 * 3600,
    "corroborate": 6 * 3600,
    "analyze": 24 * 3600,
}


def cache_disabled() -> bool:
    """Return True when the ``SRP_DISABLE_CACHE`` env var selects a bypass."""
    return os.environ.get(_DISABLE_ENV, "").strip().lower() in _TRUTHY


def _cache_root() -> Path:
    """Return the on-disk root under which pipeline caches live."""
    root = os.environ.get("SRP_DATA_DIR")
    if root:
        return Path(root) / "cache"
    return Path.home() / ".cache" / "srp"


def _make_cache(subdir: str, ttl_seconds: int) -> FilesystemCache:
    return FilesystemCache(_cache_root() / subdir, ttl_seconds=ttl_seconds)


def transcript_cache() -> FilesystemCache:
    return _make_cache("transcripts", TTL_TRANSCRIPT)


def whisper_cache() -> FilesystemCache:
    return _make_cache("whisper", TTL_WHISPER)


def summary_cache() -> FilesystemCache:
    return _make_cache("summaries", TTL_SUMMARY)


def corroboration_cache() -> FilesystemCache:
    return _make_cache("corroboration", TTL_CORROBORATION)


def stage_cache(stage_name: str) -> FilesystemCache:
    """Return the cache namespace for one pipeline stage output."""
    ttl = _STAGE_TTLS.get(stage_name, 24 * 3600)
    return _make_cache(f"stages/{stage_name}", ttl)


def hash_key(*parts: str) -> str:
    """Build a stable cache key from arbitrary strings via SHA-256 digest.

    Short raw strings (video IDs, backend names) pass through unchanged; long
    or special-character inputs (full URLs, prompts) are hashed so the
    sanitised filename stays bounded. Mixing both is safe.
    """
    joined = "\x1f".join(parts)
    if len(joined) <= 48 and all(c.isalnum() or c in "-_:" for c in joined):
        return joined.replace(":", "_")
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def get_str(cache: FilesystemCache, key: str) -> str | None:
    """Fetch a cached string, honouring the global disable flag.

    Returns ``None`` on miss, expiry, or when caching is disabled.
    """
    if cache_disabled():
        return None
    entry = cache.get(key)
    if not entry:
        return None
    value = entry.get("v")
    return value if isinstance(value, str) else None


def set_str(cache: FilesystemCache, key: str, value: str) -> None:
    """Persist a string value; becomes a no-op when caching is disabled.

    Empty strings are not cached since callers treat empty as "no result".
    """
    if cache_disabled() or not value:
        return
    cache.set(key, {"v": value})


def get_json(cache: FilesystemCache, key: str) -> dict | None:
    """Fetch a cached JSON dict, honouring the global disable flag."""
    if cache_disabled():
        return None
    return cache.get(key)


def set_json(cache: FilesystemCache, key: str, value: dict) -> None:
    """Persist a dict value; no-op when caching is disabled."""
    if cache_disabled():
        return
    cache.set(key, value)
