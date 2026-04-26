"""Tests for stage/service/technology/debug independence and priority."""

from __future__ import annotations

from pathlib import Path

import pytest
from social_research_probe.pipeline.charts import _chart_takeaways
from social_research_probe.pipeline.enrichment import _url_based_summary

from social_research_probe.commands.research import _write_final_report
from social_research_probe.config import Config
from social_research_probe.platforms.orchestrator import _auto_mode_backends, _available_backends

_ALL_STAGE_FLAGS = (
    "fetch",
    "score",
    "transcript",
    "summary",
    "corroborate",
    "stats",
    "charts",
    "synthesis",
    "assemble",
    "structured_synthesis",
    "report",
    "narration",
)

_ALL_SERVICE_FLAGS = (
    ("fetch", "platform_api"),
    ("score", "scoring"),
    ("enrich", "transcripts"),
    ("enrich", "llm"),
    ("enrich", "media_url_summary"),
    ("enrich", "merged_summary"),
    ("corroborate", "corroboration"),
    ("analyze", "statistics"),
    ("analyze", "charts"),
    ("analyze", "chart_takeaways"),
    ("youtube", "html"),
    ("youtube", "audio"),
)


@pytest.mark.parametrize("stage", _ALL_STAGE_FLAGS)
def test_each_stage_flag_can_be_disabled_individually(tmp_path, stage):
    cfg = Config.load(tmp_path)
    cfg.raw["stages"]["youtube"][stage] = False
    assert cfg.stage_enabled("youtube", stage) is False


@pytest.mark.parametrize(("section", "service"), _ALL_SERVICE_FLAGS)
def test_each_service_flag_can_be_disabled_individually(tmp_path, section, service):
    cfg = Config.load(tmp_path)
    if section == "youtube":
        cfg.raw["services"]["youtube"]["reporting"][service] = False
    else:
        cfg.raw["services"][section][service] = False
    assert cfg.service_enabled(service) is False


def test_disabling_individual_corroboration_backend_keeps_others(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["technologies"]["exa"] = False
    cfg.raw["technologies"]["llm_search"] = False
    backends = _auto_mode_backends(cfg)
    assert "exa" not in backends
    assert "llm_search" not in backends
    assert "brave" in backends
    assert "tavily" in backends


def test_stage_gate_has_priority_over_service_gate(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["stages"]["corroborate"] = False
    cfg.raw["services"]["corroborate"]["corroboration"] = True
    assert _available_backends(tmp_path, cfg=cfg) == []


def test_charts_off_takeaways_still_callable():
    """`_chart_takeaways` is a pure function; gating happens upstream."""
    assert _chart_takeaways([]) == []


@pytest.mark.asyncio
async def test_media_url_summary_silent_skip_when_service_off(tmp_path, monkeypatch):
    """Disabling services.enrich.media_url_summary must not raise."""
    cfg = Config.load(tmp_path)
    cfg.raw["services"]["enrich"]["media_url_summary"] = False
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config",
        lambda: cfg,
    )
    out = await _url_based_summary("https://y/1", word_limit=100)
    assert out is None


def test_final_report_always_emits_with_html_disabled(tmp_path):
    cfg = Config.load(tmp_path)
    cfg.raw["services"]["youtube"]["reporting"]["html"] = False
    packet = {"topic": "x", "platform": "youtube"}
    path = _write_final_report(packet, tmp_path, cfg, allow_html=True)
    assert Path(path).exists()
    assert path.endswith("report.md")


def test_final_report_renders_for_completely_empty_packet(tmp_path):
    """All-off case: a totally empty packet still produces a valid file + path."""
    cfg = Config.load(tmp_path)
    cfg.raw["services"]["youtube"]["reporting"]["html"] = False
    path = _write_final_report({}, tmp_path, cfg, allow_html=True)
    contents = Path(path).read_text()
    assert "Report" in contents


def test_final_report_obeys_allow_html_false(tmp_path):
    cfg = Config.load(tmp_path)
    path = _write_final_report({}, tmp_path, cfg, allow_html=False)
    assert path.endswith("report.md")


def test_final_report_disables_audio_report_independently(tmp_path, monkeypatch):
    cfg = Config.load(tmp_path)
    cfg.raw["services"]["youtube"]["reporting"]["audio"] = False
    captured = {}

    def fake_write_html_report(packet, data_dir, *, prepare_voicebox_audio=None):
        captured["prepare_voicebox_audio"] = prepare_voicebox_audio
        out = data_dir / "reports" / "report.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("<html></html>", encoding="utf-8")
        return out

    monkeypatch.setattr(
        "social_research_probe.render.html.write_html_report", fake_write_html_report
    )
    monkeypatch.setattr(
        "social_research_probe.render.html.serve_report_command",
        lambda path: str(path),
    )
    path = _write_final_report(
        {"topic": "x", "platform": "youtube"}, tmp_path, cfg, allow_html=True
    )
    assert path.endswith("report.html")
    assert captured["prepare_voicebox_audio"] is False
