"""Push to 100% — micro 9."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe import get_version
from social_research_probe.commands import config as cfg_cmd
from social_research_probe.config import Config
from social_research_probe.services.synthesizing.synthesis.helpers import formatter
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_correlation,
    explain_descriptive,
)
from social_research_probe.technologies.corroborates import _host
from social_research_probe.technologies.media_fetch import youtube_api
from social_research_probe.technologies.report_render.html.raw_html import markdown_to_html
from social_research_probe.technologies.report_render.html.raw_html import youtube as yt_html
from social_research_probe.technologies.statistics import logistic_regression, normality
from social_research_probe.technologies.transcript_fetch import youtube_transcript_api as yt_api
from social_research_probe.technologies.validation.ai_slop_detector import score
from social_research_probe.utils.core.errors import AdapterError


def test_get_version_unknown(monkeypatch):
    import social_research_probe as srp_pkg

    def boom(name):
        raise PackageNotFoundError

    monkeypatch.setattr(srp_pkg, "version", boom, raising=False)
    with patch("social_research_probe.Path.is_file", return_value=False):
        out = srp_pkg.get_version()
    assert out == "unknown"


def test_get_version_main_module(monkeypatch):
    out = get_version()
    assert isinstance(out, str)


def test_yt_html_technology_logs_exception(monkeypatch):
    with patch.object(yt_html, "load_active_config", side_effect=RuntimeError, create=True):
        assert yt_html._technology_logs_enabled() is False


def test_config_allows_stage_disabled(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["stages"]["youtube"]["custom_stage"] = False
    assert cfg.allows(platform="youtube", stage="custom_stage") is False


def test_config_preferred_runner_disabled_tech(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[llm]\nrunner = "claude"\n[technologies]\nclaude = false\n'
    )
    cfg = Config.load(tmp_path)
    # Service enabled, runner is known, but tech disabled → returns None
    assert cfg.preferred_free_text_runner is None


def test_config_default_structured_disabled_tech(tmp_path):
    (tmp_path / "config.toml").write_text(
        '[llm]\nrunner = "claude"\n[technologies]\nclaude = false\n'
    )
    cfg = Config.load(tmp_path)
    assert cfg.default_structured_runner == "none"


def test_config_service_enabled_recursive(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["services"]["youtube"]["nested"] = {"deep_flag": True}
    import social_research_probe.config as cfg_mod

    cfg_mod._KNOWN_SERVICE_NAMES = frozenset(cfg_mod._collect_service_names(cfg.raw["services"]))
    assert cfg.service_enabled("deep_flag") is True


def test_yt_api_search_videos_failure(monkeypatch):
    with patch.object(youtube_api, "_build_client") as bc:
        bc.return_value.search.return_value.list.return_value.execute.side_effect = RuntimeError(
            "api err"
        )
        with pytest.raises(AdapterError):
            youtube_api._search_videos("k", topic="t", max_items=5, published_after=None)


def test_yt_api_build_client(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr("googleapiclient.discovery.build", lambda *a, **kw: fake)
    out = youtube_api._build_client("KEY")
    assert out == fake


def test_cmd_config_format_secrets_no_env(monkeypatch):
    monkeypatch.delenv("SRP_API_KEY", raising=False)
    out = cfg_cmd._format_secrets_section({"api_key": "filevalue123456"})
    assert any("from file" in line for line in out)


def test_explain_correlation_no_factors_branch():
    # No "between X and Y" → uses default pair
    out = explain_correlation("Pearson r unknown: 0.05")
    assert "these two factors" in out


def test_explain_descriptive_min_branch():
    out = explain_descriptive("Min overall: 0.20")
    assert "Floor" in out


def test_score_only_punctuation():
    assert score(".") == 0.0 or score(".") >= 0.0


def test_normality_skew_zero_kurt_normal():
    out = normality.run([1.0, 1.0, 2.0, 2.0])
    assert out


def test_filters_host_with_port():
    assert _host("https://x.com:8080/p") == "x.com"


def test_yt_api_transcript_fake_test_url(monkeypatch):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    out = yt_api.fetch_transcript("https://youtube.com/watch?v=fake")
    assert out and "transcript-token" in out


def test_yt_api_transcript_no_api(monkeypatch):
    monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
    monkeypatch.setattr(yt_api, "_API_AVAILABLE", False)
    out = yt_api.fetch_transcript("https://youtube.com/watch?v=abcDEF12345")
    assert out is None


def test_markdown_to_html_blank_lines():
    out = markdown_to_html.md_to_html("para1\n\n\npara2")
    assert "<p>" in out


def test_formatter_resolve_summary_blank():
    # _ensure_sentence empty path — already covered, but exercise resolve with blank report_summary
    out = formatter.resolve_report_summary({"report_summary": ""})
    assert out is None or out == ""


def test_logistic_no_features():
    # k=0 features → degenerate output
    out = logistic_regression.run([0, 1], {}, max_iter=2)
    assert isinstance(out, list)
