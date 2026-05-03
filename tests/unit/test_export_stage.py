"""Tests for Phase 3 YouTubeExportStage and resolve_html_report_path."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from social_research_probe.platforms.state import PipelineState
from social_research_probe.platforms.youtube import YouTubeExportStage, YouTubePipeline
from social_research_probe.utils.pipeline.helpers import resolve_html_report_path


def _run(coro):
    return asyncio.run(coro)


def _state(report: dict, platform_config: dict | None = None) -> PipelineState:
    state = PipelineState(
        platform_type="youtube", cmd=None, cache=None, platform_config=platform_config or {}
    )
    state.outputs["report"] = report
    return state


def _fake_export_paths() -> dict:
    return {"sources_csv": "/tmp/s.csv", "comments_csv": "/tmp/c.csv"}


# --- resolve_html_report_path ---


def test_resolve_file_uri():
    report = {"html_report_path": "file:///Users/x/reports/r.html"}
    assert resolve_html_report_path(report) == Path("/Users/x/reports/r.html")


def test_resolve_plain_path():
    report = {"report_path": "/Users/x/reports/r.html"}
    assert resolve_html_report_path(report) == Path("/Users/x/reports/r.html")


def test_resolve_path_object():
    p = Path("/Users/x/reports/r.html")
    assert resolve_html_report_path({"html_report_path": p}) == p


def test_resolve_empty_string():
    assert resolve_html_report_path({"html_report_path": ""}) is None


def test_resolve_missing_key():
    assert resolve_html_report_path({}) is None


def test_resolve_uri_with_spaces():
    report = {"html_report_path": "file:///path/to/my%20report.html"}
    assert resolve_html_report_path(report) == Path("/path/to/my report.html")


def test_resolve_prefers_html_report_path_over_report_path():
    report = {
        "html_report_path": "file:///Users/x/r.html",
        "report_path": "srp serve-report --report /Users/x/r.html",
    }
    assert resolve_html_report_path(report) == Path("/Users/x/r.html")


def test_resolve_serve_command_not_treated_as_path():
    report = {"report_path": "srp serve-report --report /tmp/r.html"}
    assert resolve_html_report_path(report) is None


# --- YouTubeExportStage ---


def test_stage_name():
    assert YouTubeExportStage().stage_name == "export"


def test_stage_disabled_skips():
    state = _state({"html_report_path": "file:///tmp/r.html"})
    mock_cfg = MagicMock()
    mock_cfg.stage_enabled.return_value = False
    with patch("social_research_probe.config.load_active_config", return_value=mock_cfg):
        with patch(
            "social_research_probe.services.reporting.export.ExportService.execute_batch",
            new=AsyncMock(),
        ) as mock_svc:
            _run(YouTubeExportStage().execute(state))
    mock_svc.assert_not_called()


def test_stage_no_report_path_skips(tmp_path):
    state = _state({"topic": "test"})
    with patch(
        "social_research_probe.services.reporting.export.ExportService.execute_batch",
        new=AsyncMock(),
    ) as mock_svc:
        _run(YouTubeExportStage().execute(state))
    mock_svc.assert_not_called()


def test_stage_calls_export_service_with_html_report_path(tmp_path):
    html_path = tmp_path / "r.html"
    html_path.touch()
    report = {"html_report_path": html_path.as_uri()}
    state = _state(report)
    fake_result = MagicMock()
    fake_result.tech_results = [MagicMock(success=True, output=_fake_export_paths())]
    with patch(
        "social_research_probe.services.reporting.export.ExportService.execute_batch",
        new=AsyncMock(return_value=[fake_result]),
    ):
        result_state = _run(YouTubeExportStage().execute(state))

    assert result_state.outputs["report"]["export_paths"] == _fake_export_paths()


def test_stage_stores_export_paths_in_stage_output(tmp_path):
    html_path = tmp_path / "r.html"
    html_path.touch()
    report = {"html_report_path": html_path.as_uri()}
    state = _state(report)
    fake_result = MagicMock()
    fake_result.tech_results = [MagicMock(success=True, output={"sources_csv": "/tmp/s.csv"})]
    with patch(
        "social_research_probe.services.reporting.export.ExportService.execute_batch",
        new=AsyncMock(return_value=[fake_result]),
    ):
        result_state = _run(YouTubeExportStage().execute(state))

    stage_out = result_state.outputs["stages"]["export"]
    assert stage_out["export_paths"] == {"sources_csv": "/tmp/s.csv"}


def test_stage_plain_path_resolves(tmp_path):
    html_path = tmp_path / "r.html"
    html_path.touch()
    report = {"report_path": str(html_path)}
    state = _state(report)
    fake_result = MagicMock()
    fake_result.tech_results = [MagicMock(success=True, output={})]
    with patch(
        "social_research_probe.services.reporting.export.ExportService.execute_batch",
        new=AsyncMock(return_value=[fake_result]),
    ) as mock_svc:
        _run(YouTubeExportStage().execute(state))
    mock_svc.assert_called_once()


# --- Pipeline wiring ---


def test_pipeline_stages_include_export():
    all_stages = [s for group in YouTubePipeline().stages() for s in group]
    names = [s.stage_name for s in all_stages]
    assert "export" in names


def test_pipeline_export_after_report():
    groups = YouTubePipeline().stages()
    report_group_idx = next(
        i for i, g in enumerate(groups) if any(s.stage_name == "report" for s in g)
    )
    export_group_idx = next(
        i for i, g in enumerate(groups) if any(s.stage_name == "export" for s in g)
    )
    assert export_group_idx > report_group_idx
