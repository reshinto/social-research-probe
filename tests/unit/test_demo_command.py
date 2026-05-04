"""Tests for the offline demo report command orchestrator."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from social_research_probe.commands import demo
from social_research_probe.config import reset_config_cache
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.demo.constants import DEMO_DISCLAIMER


@pytest.fixture
def isolated_data_dir(monkeypatch, tmp_path) -> Path:
    """Point load_active_config at a clean tmp data dir."""
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    reset_config_cache()
    return tmp_path


def _run_demo() -> int:
    return demo.run(argparse.Namespace())


def _list_reports(data_dir: Path) -> list[Path]:
    reports_dir = data_dir / "reports"
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.iterdir())


def test_run_returns_exit_success(isolated_data_dir):
    rc = _run_demo()
    assert rc == ExitCode.SUCCESS


def test_writes_html_and_export_artifacts(isolated_data_dir):
    _run_demo()
    files = _list_reports(isolated_data_dir)
    suffixes = {f.suffix for f in files}
    assert ".html" in suffixes
    assert ".csv" in suffixes
    assert ".md" in suffixes
    assert ".json" in suffixes


def test_html_contains_disclaimer(isolated_data_dir):
    _run_demo()
    html_files = [f for f in _list_reports(isolated_data_dir) if f.suffix == ".html"]
    assert html_files, "demo did not produce an HTML report"
    contents = html_files[0].read_text(encoding="utf-8")
    assert DEMO_DISCLAIMER in contents


def test_methodology_md_contains_disclaimer(isolated_data_dir):
    _run_demo()
    md_files = [
        f for f in _list_reports(isolated_data_dir) if f.suffix == ".md" and "methodology" in f.name
    ]
    assert md_files, "methodology.md not produced"
    assert DEMO_DISCLAIMER in md_files[0].read_text(encoding="utf-8")


def test_run_summary_json_marks_topic_synthetic_and_lists_disclaimer(isolated_data_dir):
    _run_demo()
    json_files = [
        f
        for f in _list_reports(isolated_data_dir)
        if f.suffix == ".json" and "run_summary" in f.name
    ]
    assert json_files, "run_summary.json not produced"
    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert payload["topic"].startswith("[SYNTHETIC DEMO]")
    assert DEMO_DISCLAIMER in payload["warnings"]


def test_stdout_lists_five_paths(isolated_data_dir, capsys):
    _run_demo()
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 7
    for line in out:
        assert line.strip()


def test_stdout_first_line_is_html_path(isolated_data_dir, capsys):
    _run_demo()
    out = capsys.readouterr().out.strip().splitlines()
    assert out[0].endswith(".html")
    assert Path(out[0]).exists()


def test_run_summary_artifact_paths_lists_html(isolated_data_dir):
    _run_demo()
    json_files = [
        f
        for f in _list_reports(isolated_data_dir)
        if f.suffix == ".json" and "run_summary" in f.name
    ]
    payload = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert payload["artifact_paths"]["html_report"].endswith(".html")


def test_run_offline_when_external_http_blocked(isolated_data_dir, monkeypatch):
    def _refuse(*_args, **_kwargs):
        raise OSError("network disabled in test")

    monkeypatch.setattr(urllib.request, "urlopen", _refuse)
    rc = _run_demo()
    assert rc == ExitCode.SUCCESS
    files = _list_reports(isolated_data_dir)
    assert any(f.suffix == ".html" for f in files)


def test_render_html_helper_sets_report_path(isolated_data_dir):
    import asyncio

    report = {"topic": "[SYNTHETIC DEMO] x", "platform": "youtube", "items_top_n": []}
    asyncio.run(demo._render_html(report))
    assert report.get("report_path")


def test_run_short_circuits_when_html_path_unresolvable(monkeypatch, isolated_data_dir, capsys):
    async def _stub_render(report: dict) -> None:
        report["report_path"] = ""

    monkeypatch.setattr(demo, "_render_html", _stub_render)
    rc = _run_demo()
    assert rc == ExitCode.SUCCESS
    out = capsys.readouterr().out
    assert out == ""


def test_run_exports_helper_returns_empty_when_disabled(isolated_data_dir):
    import asyncio

    report = {"topic": "[SYNTHETIC DEMO]", "platform": "youtube", "items_top_n": []}
    paths = asyncio.run(
        demo._run_exports(
            report,
            {"export": {"enabled": False}},
            stem="x",
            reports_dir=isolated_data_dir,
        )
    )
    assert paths == {}


def test_run_populates_export_paths_on_report(isolated_data_dir):
    captured: dict = {}

    original_print = demo._print_paths

    def _capture(report_path: str, export_paths: dict[str, str]) -> None:
        captured["report_path"] = report_path
        captured["export_paths"] = export_paths
        original_print(report_path, export_paths)

    with patch.object(demo, "_print_paths", _capture):
        _run_demo()

    assert captured["report_path"]
    assert set(captured["export_paths"].keys()) == {
        "sources_csv",
        "comments_csv",
        "methodology_md",
        "run_summary_json",
        "claims_csv",
        "narratives_csv",
    }
