"""Tests for services.reporting.report.ReportService."""

from __future__ import annotations

import pytest

from social_research_probe.services.reporting.report import ReportService


@pytest.mark.asyncio
async def test_write_report_delegates_to_write_final_report(monkeypatch):
    calls = []

    def fake_write_final_report(report, *, allow_html):
        calls.append((report, allow_html))
        return "/fake/path/report.md"

    monkeypatch.setattr(
        "social_research_probe.services.reporting.write_final_report",
        fake_write_final_report,
    )

    svc = ReportService()
    result = await svc.execute_service(
        {"report": {"title": "test"}, "allow_html": False},
        None,
    )

    assert result.tech_results[0].output == "/fake/path/report.md"
    assert calls == [({"title": "test"}, False)]


def test_get_technologies_returns_html_render_tech():
    from social_research_probe.technologies.report_render import HtmlRenderTech

    svc = ReportService()
    techs = svc._get_technologies()
    assert len(techs) == 1
    assert isinstance(techs[0], HtmlRenderTech)


@pytest.mark.asyncio
async def test_write_report_default_allow_html_is_true(monkeypatch):
    captured = {}

    def fake_write_final_report(report, *, allow_html):
        captured["allow_html"] = allow_html
        return "/fake/path/report.html"

    monkeypatch.setattr(
        "social_research_probe.services.reporting.write_final_report",
        fake_write_final_report,
    )

    svc = ReportService()
    await svc.execute_service({"report": {}}, None)

    assert captured["allow_html"] is True
