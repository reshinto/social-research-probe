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
    (tmp_path / ".skill-data").mkdir(exist_ok=True)
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == tmp_path / "env"


def test_cwd_skill_data_beats_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    local = tmp_path / ".skill-data"
    local.mkdir(exist_ok=True)
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == local


def test_fallback_to_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SRP_DATA_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    local = tmp_path / ".skill-data"
    if local.exists():
        import shutil

        shutil.rmtree(local)
    result = resolve_data_dir(flag=None, cwd=tmp_path)
    assert result == tmp_path / "home" / ".social-research-probe"


def test_config_load_returns_defaults_when_missing(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "none"
    assert cfg.corroboration_backend == "auto"
    assert cfg.platform_defaults("youtube")["max_items"] == 20
    assert cfg.llm_settings("codex")["binary"] == "codex"
    assert cfg.stage_enabled("youtube", "fetch") is True
    assert cfg.service_enabled("llm") is True
    assert cfg.technology_enabled("claude") is False
    assert cfg.debug_enabled("technology_logs_enabled") is False
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"
    assert cfg.voicebox["default_profile_name"] == "Jarvis"


def test_config_load_reads_toml_claude(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "claude"\ntimeout_seconds = 30\n\n[technologies]\nclaude = true\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.llm_runner == "claude"
    assert cfg.llm_timeout_seconds == 30
    assert cfg.preferred_free_text_runner == "claude"
    assert cfg.default_structured_runner == "claude"


def test_config_load_reads_toml_gemini(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "gemini"\ntimeout_seconds = 30\n\n[technologies]\ngemini = true\n',
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
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "local"\n\n[technologies]\nlocal = true\n', encoding="utf-8"
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.preferred_free_text_runner == "local"
    assert cfg.default_structured_runner == "local"


def test_preferred_free_text_runner_returns_none_for_none_runner(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"


def test_llm_service_gate_disables_runner_usage_but_not_unrelated_services(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[llm]\nrunner = "claude"\n\n[technologies]\nclaude = true\n\n[services.enrich]\nllm = false\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.preferred_free_text_runner is None
    assert cfg.default_structured_runner == "none"
    assert cfg.service_enabled("llm") is False
    assert cfg.service_enabled("charts") is True


def test_config_deep_merge_preserves_defaults_for_absent_keys(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text('[llm]\nrunner = "claude"\n', encoding="utf-8")
    cfg = Config.load(tmp_data_dir)
    # Non-overridden sections still have defaults
    assert cfg.corroboration_backend == "auto"
    assert cfg.platform_defaults("youtube")["max_items"] == 20
    # Mutating cfg.raw must NOT corrupt DEFAULT_CONFIG
    cfg.raw["corroboration"]["backend"] = "mutated"
    cfg2 = Config.load(tmp_data_dir)
    assert cfg2.corroboration_backend == "auto"


def test_corroboration_backend_reads_current_value_verbatim(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[corroboration]\nbackend = "llm_search"\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.corroboration_backend == "llm_search"


def test_config_allows_applies_stage_then_service_then_technology(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        "[stages.youtube]\ncorroborate = false\n\n[services.corroborate]\ncorroboration = true\n\n[technologies]\nexa = true\n",
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert (
        cfg.allows(
            platform="youtube", stage="corroborate", service="corroboration", technology="exa"
        )
        is False
    )
    assert cfg.allows(service="corroboration", technology="exa") is True


def test_config_load_reads_voicebox_default_profile_name(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        '[voicebox]\ndefault_profile_name = "Friday"\n',
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.voicebox["default_profile_name"] == "Friday"


def test_config_load_reads_debug_and_service_tables(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        "[debug]\ntechnology_logs_enabled = true\n\n[services.youtube.reporting]\naudio = false\n",
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.debug_enabled("technology_logs_enabled") is True
    assert cfg.service_enabled("audio") is False


def test_modular_reporting_service_keys_are_used_directly(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.service_enabled("html") is True
    assert cfg.service_enabled("audio") is True


def test_modular_reporting_service_keys_can_disable_reporting(tmp_data_dir: Path):
    (tmp_data_dir / "config.toml").write_text(
        "[services.youtube.reporting]\nhtml = false\naudio = false\n",
        encoding="utf-8",
    )
    cfg = Config.load(tmp_data_dir)
    assert cfg.service_enabled("html") is False
    assert cfg.service_enabled("audio") is False


def test_service_enabled_returns_false_for_unknown_service(tmp_data_dir: Path):
    cfg = Config.load(tmp_data_dir)
    assert cfg.service_enabled("definitely_missing") is False
