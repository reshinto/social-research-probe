"""Tests for utils.caching."""

from __future__ import annotations

import os
import time
from pathlib import Path

from social_research_probe.utils.caching.cache import FilesystemCache, _sanitise_key
from social_research_probe.utils.caching.hashing import stable_hash


class TestSanitiseKey:
    def test_safe_chars_pass(self):
        assert _sanitise_key("abc-123_DEF") == "abc-123_DEF"

    def test_unsafe_replaced(self):
        assert _sanitise_key("foo/bar:baz qux") == "foo_bar_baz_qux"


class TestFilesystemCacheRoundtrip:
    def test_set_then_get(self, tmp_path: Path):
        cache = FilesystemCache(tmp_path, ttl_seconds=60)
        cache.set("k1", {"v": 1})
        assert cache.get("k1") == {"v": 1}

    def test_missing_returns_none(self, tmp_path: Path):
        cache = FilesystemCache(tmp_path)
        assert cache.get("nope") is None

    def test_expired_returns_none(self, tmp_path: Path):
        cache = FilesystemCache(tmp_path, ttl_seconds=1)
        cache.set("k", {"v": 1})
        old = time.time() - 3600
        os.utime(tmp_path / "k.json", (old, old))
        assert cache.get("k") is None

    def test_invalidate(self, tmp_path: Path):
        cache = FilesystemCache(tmp_path)
        cache.set("k", {"v": 1})
        cache.invalidate("k")
        assert cache.get("k") is None

    def test_invalidate_missing_is_noop(self, tmp_path: Path):
        cache = FilesystemCache(tmp_path)
        cache.invalidate("never-existed")

    def test_unsafe_key_storage(self, tmp_path: Path):
        cache = FilesystemCache(tmp_path)
        cache.set("foo/bar", {"x": 1})
        assert cache.get("foo/bar") == {"x": 1}


class TestStableHash:
    def test_dict_order_independent(self):
        assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})

    def test_distinct_inputs_distinct_hashes(self):
        assert stable_hash({"a": 1}) != stable_hash({"a": 2})

    def test_returns_hex_64(self):
        h = stable_hash([1, 2, 3])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
