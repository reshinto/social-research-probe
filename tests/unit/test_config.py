"""Tests for social_research_probe.config."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from social_research_probe.config import (
    DEFAULT_CONFIG,
    Config,
    _deep_merge,
    load_active_config,
    reset_config_cache,
    resolve_data_dir,
)


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    reset_config_cache()
    yield
    reset_config_cache()


def test_deep_merge_overrides():
    out = _deep_merge({"a": 1, "b": {"c": 2}}, {"b": {"c": 3, "d": 4}})
    assert out == {"a": 1, "b": {"c": 3, "d": 4}}


def test_deep_merge_replaces_when_types_differ():
    out = _deep_merge({"a": {"x": 1}}, {"a": "string"})
    assert out == {"a": "string"}


def test_resolve_data_dir_flag(tmp_path, monkeypatch):
    target = tmp_path / "flag"
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    resolve_data_dir(str(target))
    assert os.environ["SRP_DATA_DIR"] == str(target.resolve())


def test_resolve_data_dir_env_wins_over_cwd(tmp_path, monkeypatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path / "env"))
    resolve_data_dir(None, cwd=tmp_path)
    assert os.environ["SRP_DATA_DIR"] == str((tmp_path / "env").resolve())


def test_resolve_data_dir_cwd_skill_data(tmp_path, monkeypatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    cwd = tmp_path / "work"
    cwd.mkdir()
    skill = cwd / ".skill-data"
    skill.mkdir()
    resolve_data_dir(None, cwd=cwd)
    assert os.environ["SRP_DATA_DIR"] == str(skill.resolve())


def test_resolve_data_dir_fallback_home(tmp_path, monkeypatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    cwd = tmp_path / "noskill"
    cwd.mkdir()
    resolve_data_dir(None, cwd=cwd)
    assert os.environ["SRP_DATA_DIR"].endswith(".social-research-probe")


def test_load_returns_defaults_when_missing(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.llm_runner == DEFAULT_CONFIG["llm"]["runner"]
    assert cfg.corroboration_provider == "auto"


def test_load_merges_user_overrides(tmp_path):
    (tmp_path / "config.toml").write_text('[llm]\nrunner = "claude"\n')
    cfg = Config.load(tmp_path)
    assert cfg.llm_runner == "claude"


def test_llm_settings_none_returns_empty(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.llm_settings("none") == {}


def test_llm_settings_returns_dict(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.llm_settings("claude") == {"extra_flags": []}


def test_llm_timeout_seconds_int(tmp_path):
    cfg = Config.load(tmp_path)
    assert isinstance(cfg.llm_timeout_seconds, int)


def test_preferred_free_text_runner_disabled(tmp_path):
    (tmp_path / "config.toml").write_text('[llm]\nrunner = "none"\n')
    cfg = Config.load(tmp_path)
    assert cfg.preferred_free_text_runner is None


def test_default_structured_runner_none(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.default_structured_runner == "none"


def test_platform_defaults_known(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.platform_defaults("youtube")["max_items"] == 20


def test_platform_defaults_unknown(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.platform_defaults("missing") == {}


def test_apply_platform_overrides(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.apply_platform_overrides({"max_items": 99})
    assert cfg.platform_defaults("youtube")["max_items"] == 99


def test_stage_enabled_known(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.stage_enabled("youtube", "fetch") is True


def test_stage_enabled_unknown_platform(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.stage_enabled("none", "fetch") is True


def test_service_enabled_unknown(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.service_enabled("nope") is False


def test_service_enabled_known(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.service_enabled("score") is True


def test_technology_enabled(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.technology_enabled("yt_dlp") is True
    assert cfg.technology_enabled("missing-tech") is False


def test_debug_enabled(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.debug_enabled("technology_logs_enabled") is False
    assert cfg.debug_enabled("missing") is False


def test_allows_chain(tmp_path):
    cfg = Config.load(tmp_path)
    assert cfg.allows(platform="youtube", stage="fetch", technology="yt_dlp") is True
    assert cfg.allows(stage="fetch", platform=None) is False
    assert cfg.allows(technology="never-existed") is False


def test_load_active_config_caches(tmp_path):
    a = load_active_config(tmp_path)
    b = load_active_config(tmp_path)
    assert a is b


def test_reset_config_cache():
    cfg = load_active_config()
    reset_config_cache()
    assert cfg is not load_active_config()
