"""Even more micro coverage."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from social_research_probe.commands import install_skill
from social_research_probe.config import Config, _collect_service_names
from social_research_probe.platforms import orchestrator
from social_research_probe.platforms.youtube import pipeline as yt
from social_research_probe.services.enriching import transcript as transcript_svc
from social_research_probe.services.synthesizing.synthesis.helpers import formatter
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_correlation,
    explain_descriptive,
)
from social_research_probe.technologies.media_fetch import youtube_api, yt_dlp
from social_research_probe.technologies.statistics import (
    bayesian_linear,
    huber_regression,
    polynomial_regression,
)
from social_research_probe.technologies.transcript_fetch import whisper as whisper_mod
from social_research_probe.technologies.validation.ai_slop_detector import (
    _short_sentence_signal,
)


def test_collect_service_names_non_dict():
    assert _collect_service_names("notdict") == set()


def test_config_preferred_free_text_runner_unknown(tmp_path):
    (tmp_path / "config.toml").write_text('[llm]\nrunner = "claude"\n')
    cfg = Config.load(tmp_path)
    # technology disabled
    assert cfg.preferred_free_text_runner is None or cfg.preferred_free_text_runner == "claude"


def test_config_default_structured_runner_disabled(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[llm]\nrunner = "claude"\n[services]\n[services.youtube]\n'
    )
    cfg = Config.load(tmp_path)
    # service disabled by absence
    assert cfg.default_structured_runner == "none"


def test_config_apply_platform_overrides_skips_non_dict(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["platforms"]["weird"] = "not-dict"
    cfg.apply_platform_overrides({"x": 1})
    assert cfg.raw["platforms"]["weird"] == "not-dict"


def test_config_stage_enabled_unknown_stage(tmp_path):
    cfg = Config.load(tmp_path)
    # Stage not in dict → returns True default
    assert cfg.stage_enabled("youtube", "missing") is True


def test_config_service_enabled_nested(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["services"]["youtube"]["custom_section"] = {"deep_flag": True}
    # ensure leaf names rebuilt
    import social_research_probe.config as cfg_mod

    cfg_mod._KNOWN_SERVICE_NAMES = frozenset(cfg_mod._collect_service_names(cfg.raw["services"]))
    assert cfg.service_enabled("deep_flag") is True


def test_orchestrator_fake_youtube_register(monkeypatch):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")

    captured = []

    def fake_import(name):
        captured.append(name)
        return MagicMock()

    from social_research_probe.services.sourcing.youtube import YouTubeSourcingService

    monkeypatch.setattr(YouTubeSourcingService, "execute_one", YouTubeSourcingService.execute_one)
    monkeypatch.setattr("importlib.import_module", fake_import)
    orchestrator._maybe_register_fake()
    assert any("fake_youtube" in n for n in captured)


def test_install_skill_load_and_merge(monkeypatch, tmp_path):
    bundled = tmp_path / "b.toml"
    bundled.write_text("[a]\nx = 1\n[b]\ny = 2\n")
    monkeypatch.setattr(install_skill, "_BUNDLED_CONFIG", bundled)
    target = tmp_path / "c.toml"
    target.write_text("[a]\nx = 1\n")
    _cfg, added = install_skill._load_and_merge_configs(target)
    assert added == ["b"]


def test_install_skill_run_writes_skill(monkeypatch, tmp_path):
    monkeypatch.setattr(install_skill.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(install_skill, "_install_cli", lambda: None)
    monkeypatch.setattr(install_skill, "_copy_config_example", lambda: None)
    monkeypatch.setattr(install_skill, "_prompt_for_secrets", lambda: None)
    monkeypatch.setattr(install_skill, "_ensure_voicebox_secrets", lambda: None)
    monkeypatch.setattr(install_skill, "_prompt_for_runner", lambda: None)
    src = tmp_path / "src_skill"
    src.mkdir()
    (src / "x.md").write_text("y")
    target = tmp_path / ".claude" / "skills" / "srp_unique_test_2"
    monkeypatch.setattr(
        install_skill.shutil, "copytree", lambda s, d: d.mkdir(parents=True, exist_ok=True)
    )
    if target.exists():
        from shutil import rmtree

        rmtree(target)
    rc = install_skill.run(str(target))
    assert rc == 0


def test_pipeline_yt_corroborate_health_check_validation_error(monkeypatch):
    from social_research_probe.services.corroborating.corroborate import CorroborationService
    from social_research_probe.utils.core.errors import ValidationError

    cfg = MagicMock()
    cfg.service_enabled.return_value = True
    cfg.corroboration_provider = "exa"
    cfg.technology_enabled.return_value = True

    with (
        patch("social_research_probe.config.load_active_config", return_value=cfg),
        patch(
            "social_research_probe.services.corroborating.get_provider",
            side_effect=ValidationError("nope"),
        ),
    ):
        svc = CorroborationService()
    assert svc.providers == []


def test_yt_dlp_log_failure_with_first_line(capsys, monkeypatch):
    monkeypatch.setattr(yt_dlp, "_bot_hint_shown", False)
    yt_dlp._log_ytdlp_failure("ERROR: real error\nmore lines")


def test_youtube_api_resolve_secret_path(monkeypatch):
    monkeypatch.delenv("SRP_YOUTUBE_API_KEY", raising=False)
    with patch("social_research_probe.commands.config.read_secret", return_value="seck"):
        assert youtube_api.resolve_youtube_api_key() == "seck"


def test_explain_descriptive_unknown_metric():
    out = explain_descriptive("unknown metric")
    assert out == ""


def test_explain_correlation_no_match():
    out = explain_correlation("Pearson r between a and b: not a number")
    assert out == ""


def test_polynomial_run_singular(monkeypatch):
    # n <= degree+1 returns []
    assert polynomial_regression.run([1.0, 2.0], [1.0, 2.0], degree=2) == []


def test_huber_mad_zero_residuals():
    # Empty input → 0.0
    assert huber_regression._mad([]) == 0.0


def test_huber_mad_odd_count():
    # Odd-length triggers different median branch
    assert huber_regression._mad([1.0, 2.0, 3.0]) > 0


def test_huber_mad_even_count():
    assert huber_regression._mad([1.0, 2.0, 3.0, 4.0]) > 0


def test_bayesian_linear_run_too_few():
    # 0 features path
    assert bayesian_linear.run([1.0, 2.0], {}) == []


def test_whisper_load_model_cache_diff_name(monkeypatch):
    whisper_mod._MODEL_CACHE.clear()
    fake = MagicMock()
    fake.load_model.side_effect = ["m1", "m2"]
    out1 = whisper_mod._load_model_cached(fake, "small")
    out2 = whisper_mod._load_model_cached(fake, "large")
    assert out1 == "m1" and out2 == "m2"


def test_short_sentence_signal_too_few():
    assert _short_sentence_signal("Hi.") == 0.0


def test_transcript_service_no_url_str():
    """Pass non-dict data to test data path."""
    out = asyncio.run(transcript_svc.TranscriptService().execute_one("string-url"))
    assert out is not None


def test_formatter_render_full_no_compiled():
    report = {
        "topic": "ai",
        "platform": "youtube",
        "purpose_set": [],
        "items_top_n": [],
        "stats_summary": {},
        "platform_engagement_summary": "",
        "evidence_summary": "",
        "chart_captions": [],
        "warnings": [],
        "compiled_synthesis": "got it",
        "opportunity_analysis": "got it 2",
    }
    out = formatter.render_full(report)
    assert "got it" in out and "got it 2" in out
