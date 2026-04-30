"""Tests for utils.caching.pipeline_cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from social_research_probe.utils.caching import pipeline_cache as pc


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))


def test_cache_disabled_truthy(monkeypatch):
    monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
    assert pc.cache_disabled() is True
    monkeypatch.setenv("SRP_DISABLE_CACHE", "TRUE")
    assert pc.cache_disabled() is True


def test_cache_disabled_falsy(monkeypatch):
    monkeypatch.setenv("SRP_DISABLE_CACHE", "0")
    assert pc.cache_disabled() is False
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    assert pc.cache_disabled() is False


def test_cache_root_uses_data_dir(tmp_path):
    assert pc._cache_root() == tmp_path / "cache"


def test_cache_root_falls_back_to_home(monkeypatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    assert pc._cache_root() == Path.home() / ".cache" / "srp"


def test_make_cache_creates_correct_dir(tmp_path):
    cache = pc.make_cache("test_ns", 3600)
    assert cache._cache_dir == tmp_path / "cache" / "test_ns"
    assert cache._ttl == 3600


def test_ttl_overrides_applied():
    cache = pc.make_cache("fetch", pc.TTL_OVERRIDES.get("fetch", pc.DEFAULT_TTL))
    assert cache._ttl == 6 * 3600


def test_default_ttl_for_unknown():
    cache = pc.make_cache("unknown", pc.TTL_OVERRIDES.get("unknown", pc.DEFAULT_TTL))
    assert cache._ttl == 24 * 3600


class TestHashKey:
    def test_short_safe_passes_through(self):
        assert pc.hash_key("abc", "def") == "abc\x1fdef" or len(pc.hash_key("abc", "def")) == 64

    def test_short_alnum_pass_through(self):
        assert pc.hash_key("abc123") == "abc123"

    def test_colon_replaced_with_underscore(self):
        assert pc.hash_key("a:b") == "a_b"

    def test_long_input_hashed(self):
        result = pc.hash_key("x" * 60)
        assert len(result) == 64

    def test_special_char_hashed(self):
        result = pc.hash_key("foo bar")
        assert len(result) == 64


class TestGetSetJson:
    def test_roundtrip(self, tmp_path):
        cache = pc.make_cache("test_json", pc.DEFAULT_TTL)
        pc.set_json(cache, "k", {"a": 1})
        assert pc.get_json(cache, "k") == {"a": 1}

    def test_roundtrip_list(self, tmp_path):
        cache = pc.make_cache("test_json", pc.DEFAULT_TTL)
        pc.set_json(cache, "list_key", [1, 2, 3])
        assert pc.get_json(cache, "list_key") == [1, 2, 3]

    def test_roundtrip_string(self, tmp_path):
        cache = pc.make_cache("test_json", pc.DEFAULT_TTL)
        pc.set_json(cache, "str_key", "hello")
        assert pc.get_json(cache, "str_key") == "hello"

    def test_disabled(self, monkeypatch, tmp_path):
        cache = pc.make_cache("test_json", pc.DEFAULT_TTL)
        pc.set_json(cache, "k", {"a": 1})
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        assert pc.get_json(cache, "k") is None
        pc.set_json(cache, "k2", {"b": 2})


class TestEnvelopePattern:
    """Tests for _cached_execute envelope: {"input": ..., "output": ...}."""

    def test_envelope_dict_with_output_key_returns_output(self, tmp_path):
        cache = pc.make_cache("test_env", pc.DEFAULT_TTL)
        pc.set_json(cache, "ek", {"input": "repr", "output": {"x": 42}})
        raw = pc.get_json(cache, "ek")
        assert isinstance(raw, dict) and "output" in raw
        assert raw["output"] == {"x": 42}

    def test_dict_without_output_key_is_cache_miss_sentinel(self, tmp_path):
        cache = pc.make_cache("test_env", pc.DEFAULT_TTL)
        pc.set_json(cache, "old", {"some": "legacy"})
        raw = pc.get_json(cache, "old")
        assert isinstance(raw, dict) and "output" not in raw

    def test_none_on_missing_key(self, tmp_path):
        cache = pc.make_cache("test_env", pc.DEFAULT_TTL)
        assert pc.get_json(cache, "nonexistent") is None
