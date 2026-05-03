"""Filesystem-backed key/value cache with TTL expiry.

Why this exists: API adapters and pipeline stages benefit from caching expensive
network responses or computed results to disk so they survive process restarts.
``FilesystemCache`` provides a simple, dependency-free cache that stores each
entry as a ``.json`` file under a configurable directory and evicts entries
older than a TTL threshold.

Called by: platform adapters (to cache raw API responses), and any pipeline
stage that wants transparent memoisation across runs.
"""

from __future__ import annotations

import contextlib
import os
import re
import time
from pathlib import Path

from social_research_probe.utils.io.io import read_json, write_json

# Only these characters are safe in filenames across all major filesystems.
# All other characters in a cache key are replaced with an underscore.
_SAFE_KEY_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _sanitise_key(key: str) -> str:
    """Replace characters outside ``[a-zA-Z0-9_-]`` with underscores.

    Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
    from callers.

    Args:
        key: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _sanitise_key(
                key="llm.runner",
            )
        Output:
            "AI safety"
    """
    return _SAFE_KEY_RE.sub("_", key)


class FilesystemCache:
    """A simple on-disk key/value cache that stores values as JSON files.

    Each entry is stored as ``<cache_dir>/<sanitised_key>.json``. On ``get`` the file's
    modification time is compared against the configured TTL; if the entry is stale ``None``
    is returned and the file is left in place (lazy eviction).

    Lifecycle: Instantiated once per adapter or pipeline stage. The cache directory
    is created lazily on the first ``set`` call via ``write_json``.

    Examples:
        Input:
            FilesystemCache
        Output:
            FilesystemCache
    """

    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600) -> None:
        """Initialise the cache.

        Args:
            cache_dir: Filesystem location used to read, write, or resolve project data.
            ttl_seconds: Count, database id, index, or limit that bounds the work being performed.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                __init__(
                    cache_dir=Path(".skill-data"),
                    ttl_seconds=3,
                )
            Output:
                None
        """
        self._cache_dir = Path(cache_dir)
        self._ttl = ttl_seconds

    def _path_for(self, key: str) -> Path:
        """Return the filesystem path for a given cache key.

        Caching code keeps expensive provider and LLM calls repeatable while hiding storage filenames
        from callers.

        Args:
            key: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Resolved filesystem path, or None when the optional path is intentionally absent.

        Examples:
            Input:
                _path_for(
                    key="llm.runner",
                )
            Output:
                Path("report.html")
        """
        return self._cache_dir / f"{_sanitise_key(key)}.json"

    def get(self, key: str) -> object | None:
        """Return the cached value for *key*, or ``None`` if missing or expired.

        The entry is considered expired when ``time.time() - mtime > ttl_seconds``.

        Args:
            key: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                get(
                    key="llm.runner",
                )
            Output:
                "AI safety"
        """
        path = self._path_for(key)
        if not path.exists():
            return None

        # Compare file modification time against current wall-clock time.
        age = time.time() - os.path.getmtime(path)
        if age > self._ttl:
            # Entry exists but has expired; treat as a cache miss.
            return None

        return read_json(path)

    def set(self, key: str, value: object) -> None:
        """Persist *value* to disk under *key*.

        Caching helpers keep expensive provider and LLM calls repeatable without exposing storage
        filenames to callers.

        Args:
            key: Registry, config, or CLI name used to select the matching project value.
            value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                   to a provider.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                set(
                    key="llm.runner",
                    value="42",
                )
            Output:
                None
        """
        write_json(self._path_for(key), value)

    def invalidate(self, key: str) -> None:
        """Delete the cache file for *key* if it exists.

        Caching helpers keep expensive provider and LLM calls repeatable without exposing storage
        filenames to callers.

        Args:
            key: Registry, config, or CLI name used to select the matching project value.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                invalidate(
                    key="llm.runner",
                )
            Output:
                None
        """
        path = self._path_for(key)
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
