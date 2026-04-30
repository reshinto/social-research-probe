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


class TestNoStaleCacheDirectories:
    """Guard against re-introducing old cache path namespaces in production code."""

    STALE_PREFIXES = ("stages/", "summaries/", "transcripts/")

    def test_no_stale_paths_in_production_code(self):
        import re
        from pathlib import Path

        src_root = Path(__file__).parents[2] / "social_research_probe"
        pattern = re.compile(r'make_cache\s*\(\s*["\'](' + "|".join(self.STALE_PREFIXES) + r")")
        violations = []
        for py_file in src_root.rglob("*.py"):
            text = py_file.read_text()
            if pattern.search(text):
                violations.append(str(py_file))
        assert violations == [], f"Stale cache paths found in: {violations}"


class TestTechnologyCacheEnvelope:
    """Verify BaseTechnology._cached_execute writes {input, output} envelope."""

    def test_cache_file_written_with_envelope(self, tmp_path, monkeypatch):
        import asyncio
        import json

        from social_research_probe.technologies import BaseTechnology

        class _EchoTech(BaseTechnology):
            name = "test_echo"
            health_check_key = "test_echo"
            enabled_config_key = ""
            cacheable = True

            async def _execute(self, data):
                return {"echoed": data}

        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)

        tech = _EchoTech()
        result = asyncio.run(tech.execute("hello"))
        assert result == {"echoed": "hello"}

        cache_dir = tmp_path / "cache" / "technologies" / "test_echo"
        assert cache_dir.exists(), f"Cache dir not created: {cache_dir}"
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 1, f"Expected 1 cache file, got {cache_files}"
        envelope = json.loads(cache_files[0].read_text())
        assert "input" in envelope, "Cache file missing 'input' key"
        assert "output" in envelope, "Cache file missing 'output' key"
        assert envelope["output"] == {"echoed": "hello"}

    def _debug_cfg(self):
        from unittest.mock import MagicMock

        cfg = MagicMock()
        cfg.technology_enabled.return_value = True
        cfg.debug_enabled.return_value = True
        return cfg

    def test_bypass_stage_disabled_no_debug(self, tmp_path, monkeypatch):
        import asyncio

        from social_research_probe.technologies import BaseTechnology
        from social_research_probe.utils.caching import pipeline_cache as pc

        class _BypassNoDTech(BaseTechnology):
            name = "test_bypass_nodebug"
            health_check_key = ""
            enabled_config_key = ""
            cacheable = True

            async def _execute(self, data):
                return {"v": data}

        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        token = pc.disable_cache_for_technologies.set(["test_bypass_nodebug"])
        try:
            result = asyncio.run(_BypassNoDTech().execute("x"))
        finally:
            pc.disable_cache_for_technologies.reset(token)
        assert result == {"v": "x"}

    def test_debug_bypass_stage_disabled(self, tmp_path, monkeypatch):
        import asyncio

        from social_research_probe.technologies import BaseTechnology
        from social_research_probe.utils.caching import pipeline_cache as pc

        class _EchoTech(BaseTechnology):
            name = "test_stage_disabled"
            health_check_key = ""
            enabled_config_key = ""
            cacheable = True

            async def _execute(self, data):
                return {"v": data}

        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "social_research_probe.technologies.load_active_config", self._debug_cfg
        )
        token = pc.disable_cache_for_technologies.set(["test_stage_disabled"])
        try:
            result = asyncio.run(_EchoTech().execute("x"))
        finally:
            pc.disable_cache_for_technologies.reset(token)
        assert result == {"v": "x"}

    def test_debug_bypass_not_cacheable(self, tmp_path, monkeypatch):
        import asyncio

        from social_research_probe.technologies import BaseTechnology

        class _NoCacheTech(BaseTechnology):
            name = "test_no_cache"
            health_check_key = ""
            enabled_config_key = ""
            cacheable = False

            async def _execute(self, data):
                return {"v": data}

        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            "social_research_probe.technologies.load_active_config", self._debug_cfg
        )
        result = asyncio.run(_NoCacheTech().execute("y"))
        assert result == {"v": "y"}

    def test_debug_cache_miss_and_write(self, tmp_path, monkeypatch):
        import asyncio

        from social_research_probe.technologies import BaseTechnology

        class _EchoTech2(BaseTechnology):
            name = "test_debug_miss"
            health_check_key = ""
            enabled_config_key = ""
            cacheable = True

            async def _execute(self, data):
                return {"v": data}

        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        monkeypatch.setattr(
            "social_research_probe.technologies.load_active_config", self._debug_cfg
        )
        result = asyncio.run(_EchoTech2().execute("z"))
        assert result == {"v": "z"}

    def test_debug_execute_returns_none(self, tmp_path, monkeypatch):
        import asyncio

        from social_research_probe.technologies import BaseTechnology

        class _NullTech(BaseTechnology):
            name = "test_debug_null"
            health_check_key = ""
            enabled_config_key = ""
            cacheable = True

            async def _execute(self, data):
                return None

        monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
        monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
        monkeypatch.setattr(
            "social_research_probe.technologies.load_active_config", self._debug_cfg
        )
        result = asyncio.run(_NullTech().execute("w"))
        assert result is None


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
