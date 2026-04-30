"""Pipeline-wide caching helpers built on FilesystemCache.

Cache root is taken from ``SRP_DATA_DIR`` (set by the orchestrator) so each
data directory has its own isolated cache. Caching is bypassed when
``SRP_DISABLE_CACHE=1`` (useful for benchmarking or forcing a refresh).
"""

from __future__ import annotations

import contextvars
import hashlib
import os
from pathlib import Path

from social_research_probe.utils.caching.cache import FilesystemCache

_DISABLE_ENV = "SRP_DISABLE_CACHE"
_TRUTHY = {"1", "true", "yes", "on"}

_6H = 6 * 3600
_1D = 24 * 3600
_7D = 7 * 24 * 3600

DEFAULT_TTL = _1D

TTL_OVERRIDES: dict[str, int] = {
    "fetch": _6H,
    "youtube_search": _6H,
    "corroborate": _6H,
    "narration": _7D,
}

disable_cache_for_technologies: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "disable_cache_for_technologies",
    default=None,
)


def cache_disabled() -> bool:
    """Return True when the ``SRP_DISABLE_CACHE`` env var selects a bypass."""
    return os.environ.get(_DISABLE_ENV, "").strip().lower() in _TRUTHY


def _cache_root() -> Path:
    """Return the on-disk root under which pipeline caches live."""
    root = os.environ.get("SRP_DATA_DIR")
    if root:
        return Path(root) / "cache"
    return Path.home() / ".cache" / "srp"


def make_cache(subdir: str, ttl_seconds: int) -> FilesystemCache:
    return FilesystemCache(_cache_root() / subdir, ttl_seconds=ttl_seconds)


def hash_key(*parts: str) -> str:
    """Build a stable cache key from arbitrary strings via SHA-256 digest."""
    joined = "\x1f".join(parts)
    if len(joined) <= 48 and all(c.isalnum() or c in "-_:" for c in joined):
        return joined.replace(":", "_")
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def get_json(cache: FilesystemCache, key: str) -> object | None:
    """Fetch a cached value, honouring the global disable flag."""
    if cache_disabled():
        return None
    return cache.get(key)


def set_json(cache: FilesystemCache, key: str, value: object) -> None:
    """Persist a value; no-op when caching is disabled."""
    if cache_disabled():
        return
    cache.set(key, value)
