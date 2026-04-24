"""
Tests for ``social_research_probe.utils.cache``.

Verifies that ``FilesystemCache`` correctly stores and retrieves values, honours
TTL expiry (via monkeypatched ``time.time``), supports explicit invalidation,
and sanitises unsafe characters in cache keys to produce safe filenames.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from social_research_probe.utils.cache import FilesystemCache


def test_get_returns_none_when_missing(tmp_path: Path) -> None:
    """get must return None for a key that has never been set."""
    cache = FilesystemCache(tmp_path)
    assert cache.get("no_such_key") is None


def test_set_then_get_returns_value(tmp_path: Path) -> None:
    """A value written with set must be retrievable with get."""
    cache = FilesystemCache(tmp_path)
    data = {"result": [1, 2, 3]}
    cache.set("my_key", data)

    assert cache.get("my_key") == data


def test_get_expired_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """get must return None for an entry whose age exceeds ttl_seconds.

    We set TTL=1 second, write an entry, then monkeypatch ``time.time`` to
    return a value 2 seconds in the future so the entry appears expired.
    """
    import time as time_module

    cache = FilesystemCache(tmp_path, ttl_seconds=1)
    cache.set("key", {"data": "value"})

    real_time = time_module.time()

    # Advance the clock by 2 seconds so the 1-second TTL is exceeded.
    monkeypatch.setattr(
        "social_research_probe.utils.cache.time.time",
        lambda: real_time + 2,
    )

    assert cache.get("key") is None


def test_invalidate_removes_cache_entry(tmp_path: Path) -> None:
    """invalidate must cause get to return None for the affected key."""
    cache = FilesystemCache(tmp_path)
    cache.set("to_remove", {"keep": False})

    cache.invalidate("to_remove")

    assert cache.get("to_remove") is None


def test_key_sanitisation(tmp_path: Path) -> None:
    """Special characters in keys must be replaced so the file has a safe name."""
    cache = FilesystemCache(tmp_path)
    unsafe_key = "https://example.com/path?q=1&r=2"
    cache.set(unsafe_key, {"ok": True})

    # The on-disk filename must not contain any unsafe characters.
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    filename = files[0].name
    # All characters (excluding the .json extension) should be safe.
    stem = filename[: -len(".json")]
    assert all(
        c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in stem
    )

    # The value must still be retrievable via the original key.
    assert cache.get(unsafe_key) == {"ok": True}


def test_invalidate_nonexistent_key_is_noop(tmp_path: Path) -> None:
    """Lines 149-151: invalidating a key never set must not raise (FileNotFoundError is swallowed)."""
    cache = FilesystemCache(tmp_path)
    cache.invalidate("never_set_key")  # must not raise
