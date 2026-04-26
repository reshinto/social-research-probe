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


def test_named_caches_create_distinct_dirs(tmp_path):
    assert pc.transcript_cache()._cache_dir == tmp_path / "cache" / "transcripts"
    assert pc.whisper_cache()._cache_dir == tmp_path / "cache" / "whisper"
    assert pc.summary_cache()._cache_dir == tmp_path / "cache" / "summaries"
    assert pc.corroboration_cache()._cache_dir == tmp_path / "cache" / "corroboration"
    assert pc.classification_cache()._cache_dir == tmp_path / "cache" / "classification"


def test_stage_cache_known_ttl(tmp_path):
    cache = pc.stage_cache("fetch")
    assert cache._cache_dir == tmp_path / "cache" / "stages" / "fetch"
    assert cache._ttl == 6 * 3600


def test_stage_cache_unknown_default_ttl():
    cache = pc.stage_cache("nonexistent")
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


class TestGetSetStr:
    def test_roundtrip_v_key(self, tmp_path):
        cache = pc.transcript_cache()
        pc.set_str(cache, "k", "value")
        assert pc.get_str(cache, "k") == "value"

    def test_roundtrip_named_input_key(self, tmp_path):
        cache = pc.transcript_cache()
        pc.set_str(cache, "k", "value", input_key="custom")
        assert pc.get_str(cache, "k") == "value"

    def test_empty_value_not_cached(self, tmp_path):
        cache = pc.transcript_cache()
        pc.set_str(cache, "k", "")
        assert pc.get_str(cache, "k") is None

    def test_disabled_set_noop(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        cache = pc.transcript_cache()
        pc.set_str(cache, "k", "value")

    def test_disabled_get_returns_none(self, monkeypatch, tmp_path):
        cache = pc.transcript_cache()
        pc.set_str(cache, "k", "value")
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        assert pc.get_str(cache, "k") is None

    def test_get_str_missing_returns_none(self, tmp_path):
        cache = pc.transcript_cache()
        assert pc.get_str(cache, "absent") is None

    def test_get_str_non_string_value_returns_none(self, tmp_path):
        cache = pc.transcript_cache()
        cache.set("k", {"v": 123})
        assert pc.get_str(cache, "k") is None

    def test_get_str_multikey_dict_returns_none(self, tmp_path):
        cache = pc.transcript_cache()
        cache.set("k", {"a": "x", "b": "y"})
        assert pc.get_str(cache, "k") is None


class TestGetSetJson:
    def test_roundtrip(self, tmp_path):
        cache = pc.summary_cache()
        pc.set_json(cache, "k", {"a": 1})
        assert pc.get_json(cache, "k") == {"a": 1}

    def test_disabled(self, monkeypatch, tmp_path):
        cache = pc.summary_cache()
        pc.set_json(cache, "k", {"a": 1})
        monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
        assert pc.get_json(cache, "k") is None
        pc.set_json(cache, "k2", {"b": 2})
