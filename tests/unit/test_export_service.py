"""Tests for Phase 3 ExportService."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from social_research_probe.services.reporting.export import ExportService


def _run(coro):
    return asyncio.run(coro)


def _make_input(tmp_path: Path) -> dict:
    return {
        "report": {"topic": "test", "platform": "youtube"},
        "config": {
            "platforms": {"youtube": {"export": {"enabled": True}}},
            "scoring": {"weights": {}},
            "technologies": {"export_package": True},
        },
        "stem": "test-youtube-20260502",
        "reports_dir": tmp_path,
    }


def test_service_name():
    assert ExportService.service_name == "youtube.reporting.export"


def test_enabled_config_key():
    assert ExportService.enabled_config_key == "services.youtube.reporting.export"


def test_execute_service_success(tmp_path: Path):
    fake_paths = {"sources_csv": "/tmp/s.csv", "comments_csv": "/tmp/c.csv"}

    async def fake_execute(data):
        return fake_paths

    svc = ExportService()
    with patch.object(
        svc._get_technologies()[0].__class__, "_execute", new=AsyncMock(return_value=fake_paths)
    ):
        result = _run(svc.execute_service(_make_input(tmp_path), _dummy_result()))

    assert result.service_name == "youtube.reporting.export"
    assert len(result.tech_results) == 1
    tr = result.tech_results[0]
    assert tr.success is True
    assert tr.output == fake_paths


def test_execute_service_non_dict_input(tmp_path: Path):
    svc = ExportService()
    with patch.object(
        svc._get_technologies()[0].__class__,
        "_execute",
        new=AsyncMock(return_value={}),
    ):
        result = _run(svc.execute_service("bad-input", _dummy_result()))

    assert result.service_name == "youtube.reporting.export"
    tr = result.tech_results[0]
    assert tr.success is True
    assert tr.output == {}


def test_execute_batch_returns_result(tmp_path: Path):
    fake_paths = {"sources_csv": str(tmp_path / "s.csv")}
    with patch(
        "social_research_probe.technologies.report_render.export.ExportPackageTech._execute",
        new=AsyncMock(return_value=fake_paths),
    ):
        results = _run(ExportService().execute_batch([_make_input(tmp_path)]))

    assert len(results) == 1
    assert results[0].tech_results[0].output == fake_paths


def _dummy_result():
    from social_research_probe.services import ServiceResult

    return ServiceResult(
        service_name="youtube.reporting.export", input_key="export", tech_results=[]
    )
