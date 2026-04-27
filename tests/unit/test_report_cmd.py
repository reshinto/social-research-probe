"""Tests for commands.report."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.commands import report
from social_research_probe.utils.core.errors import ValidationError


def test_load_invalid_path():
    with pytest.raises(ValidationError):
        report._load_and_validate_report("/nope/x.json")


def test_load_invalid_json(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("{")
    with pytest.raises(ValidationError):
        report._load_and_validate_report(str(path))


def test_load_non_object(tmp_path):
    path = tmp_path / "x.json"
    path.write_text("[]")
    with pytest.raises(ValidationError):
        report._load_and_validate_report(str(path))


def test_load_unwraps(tmp_path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"kind": "synthesis", "report": {"a": 1}}))
    out = report._load_and_validate_report(str(path))
    assert out == {"a": 1}


def test_read_text_file_none():
    assert report._read_text_file(None) is None


def test_read_text_file_strip(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("hello  ")
    assert report._read_text_file(str(path)) == "hello"


def test_read_text_file_empty(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("")
    assert report._read_text_file(str(path)) is None


def test_read_text_file_oserror():
    with pytest.raises(ValidationError):
        report._read_text_file("/nope/missing.txt")


def test_apply_text_overrides_with_files(tmp_path):
    cs = tmp_path / "cs.txt"
    cs.write_text("compiled")
    out = report._apply_text_overrides({"a": 1}, str(cs), None, None)
    assert out["compiled_synthesis"] == "compiled"


def test_apply_text_overrides_none():
    out = report._apply_text_overrides({"a": 1}, None, None, None)
    assert out == {"a": 1}


def test_run_disabled_html(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"platform": "youtube"}))
    cfg = MagicMock()
    cfg.stage_enabled.return_value = False
    cfg.service_enabled.return_value = True
    with patch("social_research_probe.commands.report.load_active_config", return_value=cfg):
        with pytest.raises(ValidationError):
            report.run(str(path), None, None, None, str(tmp_path / "out.html"))


def test_run_to_stdout(tmp_path, monkeypatch, capsys):
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"platform": "youtube"}))

    cfg = MagicMock()
    cfg.stage_enabled.return_value = True
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = False

    monkeypatch.setattr(
        "social_research_probe.technologies.report_render.html.raw_html.youtube.render_html",
        lambda *a, **kw: "<html/>",
    )
    monkeypatch.setattr(
        "social_research_probe.technologies.report_render.html.raw_html.youtube._technology_logs_enabled",
        lambda: False,
    )
    monkeypatch.setattr(
        "social_research_probe.technologies.report_render.html.raw_html.youtube._voicebox_api_base",
        lambda: "http://x",
    )
    with patch("social_research_probe.commands.report.load_active_config", return_value=cfg):
        rc = report.run(str(path), None, None, None, None)
    assert rc == 0
    assert "<html/>" in capsys.readouterr().out
