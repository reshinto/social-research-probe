"""
Filesystem-backed key/value cache with TTL expiry.

Why this exists: API adapters and pipeline stages benefit from caching expensive
network responses or computed results to disk so they survive process restarts.
``FilesystemCache`` provides a simple, dependency-free cache that stores each
entry as a ``.json`` file under a configurable directory and evicts entries
older than a TTL threshold.

Called by: platform adapters (to cache raw API responses), and any pipeline
stage that wants transparent memoisation across runs.
"""

from __future__ import annotations

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

    Args:
        key: Raw cache key (may contain slashes, spaces, colons, etc.).

    Returns:
        A filename-safe version of the key.

    Why this exists:
        Cache keys are often derived from URLs or user-supplied strings that
        contain characters illegal or dangerous in filenames (e.g. ``/``,
        ``:``, whitespace).  Sanitising to a restricted alphabet avoids both
        OS errors and potential path-traversal issues.
    """
    return _SAFE_KEY_RE.sub("_", key)


class FilesystemCache:
    """A simple on-disk key/value cache that stores values as JSON files.

    Each entry is stored as ``<cache_dir>/<sanitised_key>.json``.  On ``get``
    the file's modification time is compared against the configured TTL; if the
    entry is stale ``None`` is returned and the file is left in place (lazy
    eviction).

    Lifecycle:
        Instantiated once per adapter or pipeline stage.  The cache directory
        is created lazily on the first ``set`` call via ``write_json``.

    Args:
        cache_dir: Directory under which cache files are stored.  Created
            automatically when the first entry is written.
        ttl_seconds: Maximum age (in seconds) of a cache entry before it is
            considered expired.  Defaults to 3600 (one hour).
    """

    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600) -> None:
        """Initialise the cache.

        Args:
            cache_dir: Root directory for cache files.
            ttl_seconds: Entry lifetime in seconds (default 3600).
        """
        self._cache_dir = Path(cache_dir)
        self._ttl = ttl_seconds

    def _path_for(self, key: str) -> Path:
        """Return the filesystem path for a given cache key.

        Args:
            key: Raw cache key.

        Returns:
            Absolute ``Path`` to the corresponding ``.json`` file.
        """
        return self._cache_dir / f"{_sanitise_key(key)}.json"

    def get(self, key: str) -> object | None:
        """Return the cached value for *key*, or ``None`` if missing or expired.

        The entry is considered expired when
        ``time.time() - mtime > ttl_seconds``.

        Args:
            key: Cache key to look up.

        Returns:
            The cached value if the entry exists and is within TTL, otherwise
            ``None``.

        Why this exists:
            Lazy TTL evaluation (checking age on read rather than running a
            background eviction thread) keeps the implementation simple and
            avoids threading concerns.
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

        Args:
            key: Cache key.
            value: JSON-serialisable value to cache.

        Returns:
            None

        Why this exists:
            Delegating to ``write_json`` gives us atomic writes for free,
            so a crash during ``set`` cannot corrupt an existing entry.
        """
        write_json(self._path_for(key), value)

    def invalidate(self, key: str) -> None:
        """Delete the cache file for *key* if it exists.

        Args:
            key: Cache key to invalidate.

        Returns:
            None

        Why this exists:
            Explicit invalidation is needed when upstream data changes (e.g.
            after a forced refresh) and stale cached data must not be served
            even within the TTL window.
        """
        path = self._path_for(key)
        import contextlib

        with contextlib.suppress(FileNotFoundError):
            path.unlink()
