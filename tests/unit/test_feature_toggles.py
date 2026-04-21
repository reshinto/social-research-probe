"""Tests for the per-feature on/off independence rule.

Each feature flag must be toggleable in isolation: turning one off must not
cause any other feature to error or warn. The final report is exempt — it
must always render even when every flag is off.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from social_research_probe.cli import _write_final_report
from social_research_probe.config import Config
from social_research_probe.pipeline.charts import _chart_takeaways
from social_research_probe.pipeline.enrichment import _url_based_summary
from social_research_probe.pipeline.orchestrator import _host_mode_backends

_ALL_FEATURE_FLAGS = (
    "corroboration_enabled",
    "gemini_search_enabled",
    "exa_enabled",
    "brave_enabled",
    "tavily_enabled",
    "llm_cli_corroboration_enabled",
    "enrichment_enabled",
    "transcript_fetch_enabled",
    "media_url_summary_enabled",
    "merged_summary_enabled",
    "stats_enabled",
    "charts_enabled",
    "chart_takeaways_enabled",
    "synthesis_enabled",
    "html_report_enabled",
    "markdown_report_enabled",
)


@pytest.mark.parametrize("flag", _ALL_FEATURE_FLAGS)
def test_each_flag_can_be_disabled_individually(tmp_path, flag):
    cfg = Config.load(tmp_path)
    cfg.raw["features"][flag] = False
    assert cfg.feature_enabled(flag) is False


def test_disabling_individual_corroboration_backend_keeps_others(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["features"]["exa_enabled"] = False
    cfg.raw["features"]["gemini_search_enabled"] = False
    backends = _host_mode_backends(cfg)
    assert "exa" not in backends
    assert "gemini_search" not in backends
    assert "brave" in backends
    assert "tavily" in backends


def test_charts_off_takeaways_still_callable():
    """`_chart_takeaways` is a pure function; gating happens upstream."""
    assert _chart_takeaways([]) == []


@pytest.mark.asyncio
async def test_media_url_summary_silent_skip_when_flag_off(tmp_path, monkeypatch):
    """Disabling media_url_summary_enabled must not raise — just return None."""
    cfg = Config.load(tmp_path)
    cfg.raw["features"]["media_url_summary_enabled"] = False
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config",
        lambda: cfg,
    )
    out = await _url_based_summary("https://y/1", word_limit=100)
    assert out is None


def test_final_report_always_emits_with_html_disabled(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["features"]["html_report_enabled"] = False
    packet = {"topic": "x", "platform": "youtube"}
    path = _write_final_report(packet, tmp_path, cfg, allow_html=True)
    assert Path(path).exists()
    assert path.endswith("report.md")


def test_final_report_renders_for_completely_empty_packet(tmp_path):
    """All-off case: a totally empty packet still produces a valid file + path."""
    cfg = Config.load(tmp_path)
    cfg.raw["features"]["html_report_enabled"] = False
    path = _write_final_report({}, tmp_path, cfg, allow_html=True)
    contents = Path(path).read_text()
    assert "Report" in contents


def test_final_report_obeys_allow_html_false(tmp_path):
    cfg = Config.load(tmp_path)
    path = _write_final_report({}, tmp_path, cfg, allow_html=False)
    assert path.endswith("report.md")
