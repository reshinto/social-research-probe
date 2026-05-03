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
    """Return True when the ``SRP_DISABLE_CACHE`` env var selects a bypass.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            cache_disabled()
        Output:
            True
    """
    return os.environ.get(_DISABLE_ENV, "").strip().lower() in _TRUTHY


def _cache_root() -> Path:
    """Return the on-disk root under which pipeline caches live.

    Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
    from callers.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _cache_root()
        Output:
            Path("report.html")
    """
    root = os.environ.get("SRP_DATA_DIR")
    if root:
        return Path(root) / "cache"
    return Path.home() / ".cache" / "srp"


def make_cache(subdir: str, ttl_seconds: int) -> FilesystemCache:
    """Build cache for the next caller.

    Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
    from callers.

    Args:
        subdir: Filesystem location used to read, write, or resolve project data.
        ttl_seconds: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            make_cache(
                subdir=Path(".skill-data"),
                ttl_seconds=3,
            )
        Output:
            "AI safety"
    """
    return FilesystemCache(_cache_root() / subdir, ttl_seconds=ttl_seconds)


def hash_key(*parts: str) -> str:
    """Build a stable cache key from arbitrary strings via SHA-256 digest.

    Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
    from callers.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            hash_key()
        Output:
            "AI safety"
    """
    joined = "\x1f".join(parts)
    if len(joined) <= 48 and all(c.isalnum() or c in "-_:" for c in joined):
        return joined.replace(":", "_")
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def get_json(cache: FilesystemCache, key: str) -> object | None:
    """Fetch a cached value, honouring the global disable flag.

    Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
    from callers.

    Args:
        cache: Pipeline cache instance used for this read or write.
        key: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            get_json(
                cache="AI safety",
                key="llm.runner",
            )
        Output:
            "AI safety"
    """
    if cache_disabled():
        return None
    return cache.get(key)


def set_json(cache: FilesystemCache, key: str, value: object) -> None:
    """Persist a value; no-op when caching is disabled.

    Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
    from callers.

    Args:
        cache: Pipeline cache instance used for this read or write.
        key: Registry, config, or CLI name used to select the matching project value.
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            set_json(
                cache="AI safety",
                key="llm.runner",
                value="42",
            )
        Output:
            None
    """
    if cache_disabled():
        return
    cache.set(key, value)
