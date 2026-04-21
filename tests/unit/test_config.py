"""Data-dir resolution order and config.toml loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from social_research_probe.config import Config, load_active_config, resolve_data_dir


def test_data_dir_flag_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path / "env"))
    result = resolve_data_dir(flag=str(tmp_path / "flag"), cwd=tmp_path)
    assert result == tmp_path / "flag"


def test_env_var_beats_cwd_and_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path / "env"))
    (tmp_path / ".skill-data").mkdir()
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == tmp_path / "env"


def test_cwd_skill_data_beats_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    local = tmp_path / ".skill-data"
    local.mkdir()
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == local


def test_fallback_to_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == tmp_path / "home" / ".social-research-probe"


def test_config_load_returns_defaults_when_missing(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "none"
    assert cfg.corroboration_backend == "host"
    assert cfg.platform_defaults("youtube")["max_items"] == 20
    assert cfg.llm_settings("codex")["binary"] == "codex"
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"


def test_config_load_reads_toml_claude(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "claude"\ntimeout_seconds = 30\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "claude"
    assert cfg.llm_timeout_seconds == 30
    assert cfg.preferred_free_text_runner == "claude"
    assert cfg.default_structured_runner == "claude"


def test_config_load_reads_toml_gemini(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "gemini"\ntimeout_seconds = 30\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "gemini"
    assert cfg.llm_timeout_seconds == 30
    assert cfg.preferred_free_text_runner == "gemini"
    assert cfg.default_structured_runner == "gemini"


def test_llm_settings_none_returns_empty_dict(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_settings("none") == {}


def test_load_active_config_uses_resolved_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "active"
    monkeypatch.setenv("SRP_DATA_DIR", str(data_dir))
    cfg = load_active_config()
    assert cfg.data_dir == data_dir


def test_preferred_free_text_runner_returns_local_when_configured(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text('[llm]\nrunner = "local"\n', encoding="utf-8")
    cfg = Config.load(tmp_data_dir)
    assert cfg.preferred_free_text_runner == "local"
    assert cfg.default_structured_runner == "local"


def test_preferred_free_text_runner_returns_none_for_none_runner(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"


def test_config_deep_merge_preserves_defaults_for_absent_keys(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text('[llm]\nrunner = "claude"\n', encoding="utf-8")
    cfg = Config.load(tmp_data_dir)
    # Non-overridden sections still have defaults
    assert cfg.corroboration_backend == "host"
    assert cfg.platform_defaults("youtube")["max_items"] == 20
    # Mutating cfg.raw must NOT corrupt DEFAULT_CONFIG
    cfg.raw["corroboration"]["backend"] = "mutated"
    cfg2 = Config.load(tmp_data_dir)
    assert cfg2.corroboration_backend == "host"


def test_corroboration_backend_normalizes_legacy_llm_cli(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[corroboration]\nbackend = "llm_cli"\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.corroboration_backend == "llm_search"
