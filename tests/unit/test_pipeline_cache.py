"""Tests for utils/pipeline_cache.py — TTL factories, disable flag, key hashing."""

from __future__ import annotations

from pathlib import Path

import pytest

from social_research_probe.utils.caching import pipeline_cache


@pytest.fixture
def _cache_dir(tmp_path, monkeypatch) -> Path:
    """Point the cache root at a fresh temp directory and leave the flag off."""
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    return tmp_path / "cache"


def test_factories_use_configured_data_dir(_cache_dir):
    transcript = pipeline_cache.transcript_cache()
    pipeline_cache.set_str(transcript, "abc", "hello")
    assert (_cache_dir / "transcripts" / "abc.json").exists()


def test_factories_use_home_when_data_dir_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cache = pipeline_cache.transcript_cache()
    pipeline_cache.set_str(cache, "abc", "hi")
    assert (tmp_path / ".cache" / "srp" / "transcripts" / "abc.json").exists()


def test_disable_env_skips_read_and_write(_cache_dir, monkeypatch):
    cache = pipeline_cache.summary_cache()
    pipeline_cache.set_str(cache, "k", "value")
    assert (_cache_dir / "summaries" / "k.json").exists()

    monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
    assert pipeline_cache.get_str(cache, "k") is None
    pipeline_cache.set_str(cache, "k2", "should-not-persist")
    assert not (_cache_dir / "summaries" / "k2.json").exists()


def test_set_str_ignores_empty_values(_cache_dir):
    cache = pipeline_cache.summary_cache()
    pipeline_cache.set_str(cache, "k", "")
    assert pipeline_cache.get_str(cache, "k") is None


def test_set_str_roundtrips_non_empty(_cache_dir):
    cache = pipeline_cache.summary_cache()
    pipeline_cache.set_str(cache, "k", "hello")
    assert pipeline_cache.get_str(cache, "k") == "hello"


def test_set_str_uses_input_key_when_provided(_cache_dir):
    cache = pipeline_cache.summary_cache()
    pipeline_cache.set_str(cache, "hash", "hello", input_key="prompt text")
    assert cache.get("hash") == {"prompt text": "hello"}
    assert pipeline_cache.get_str(cache, "hash") == "hello"


def test_get_str_reads_legacy_v_field(_cache_dir):
    cache = pipeline_cache.summary_cache()
    cache.set("k", {"v": "hello"})
    assert pipeline_cache.get_str(cache, "k") == "hello"


def test_get_str_returns_none_on_missing(_cache_dir):
    cache = pipeline_cache.summary_cache()
    assert pipeline_cache.get_str(cache, "absent") is None


def test_get_str_returns_none_when_entry_lacks_string_value(_cache_dir):
    cache = pipeline_cache.summary_cache()
    cache.set("k", {"other": 1})
    assert pipeline_cache.get_str(cache, "k") is None


def test_get_json_and_set_json_roundtrip(_cache_dir):
    cache = pipeline_cache.corroboration_cache()
    pipeline_cache.set_json(cache, "claim", {"verdict": "confirms"})
    assert pipeline_cache.get_json(cache, "claim") == {"verdict": "confirms"}


def test_get_json_returns_none_when_disabled(_cache_dir, monkeypatch):
    cache = pipeline_cache.corroboration_cache()
    pipeline_cache.set_json(cache, "k", {"a": 1})
    monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
    assert pipeline_cache.get_json(cache, "k") is None


def test_set_json_skipped_when_disabled(_cache_dir, monkeypatch):
    cache = pipeline_cache.corroboration_cache()
    monkeypatch.setenv("SRP_DISABLE_CACHE", "1")
    pipeline_cache.set_json(cache, "k", {"a": 1})
    # Re-enable to confirm nothing was persisted.
    monkeypatch.delenv("SRP_DISABLE_CACHE")
    assert pipeline_cache.get_json(cache, "k") is None


def test_hash_key_passes_through_short_safe_strings():
    assert pipeline_cache.hash_key("abc123") == "abc123"
    assert pipeline_cache.hash_key("video_id", "base") == pipeline_cache.hash_key(
        "video_id", "base"
    )


def test_hash_key_hashes_long_or_unsafe_inputs():
    long_url = "https://example.com/very/long/path?with=query&chars=" + "x" * 50
    digest = pipeline_cache.hash_key(long_url)
    assert len(digest) == 64  # sha256 hex length
    assert digest.isalnum()


def test_hash_key_replaces_colons_on_passthrough():
    out = pipeline_cache.hash_key("a:b")
    assert ":" not in out


def test_cache_disabled_defaults_to_false(_cache_dir):
    assert pipeline_cache.cache_disabled() is False


def test_cache_disabled_honors_truthy_values(_cache_dir, monkeypatch):
    for value in ("1", "true", "YES", "on"):
        monkeypatch.setenv("SRP_DISABLE_CACHE", value)
        assert pipeline_cache.cache_disabled() is True


def test_whisper_cache_writes_under_whisper_dir(_cache_dir):
    cache = pipeline_cache.whisper_cache()
    pipeline_cache.set_str(cache, "v1", "text")
    assert (_cache_dir / "whisper" / "v1.json").exists()
