"""Sweep remaining 1-line gaps."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import social_research_probe.services.scoring as compute_mod
from social_research_probe.commands import install_skill
from social_research_probe.services.enriching import transcript as transcript_svc
from social_research_probe.services.reporting import html as html_svc
from social_research_probe.services.synthesizing.synthesis.helpers import formatter
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_correlation,
    explain_descriptive,
)
from social_research_probe.technologies.corroborates import _host
from social_research_probe.technologies.media_fetch import youtube_api
from social_research_probe.technologies.report_render.html.raw_html import (
    markdown_to_html,
)
from social_research_probe.technologies.report_render.html.raw_html import (
    youtube as yt_html,
)
from social_research_probe.technologies.statistics import (
    _compute,
    bayesian_linear,
    growth,
    normality,
)
from social_research_probe.technologies.validation.ai_slop_detector import score


def test_install_skill_run_existing_dest(monkeypatch, tmp_path):
    """Cover the `if dest.exists(): rmtree` branch."""
    monkeypatch.setattr(install_skill.Path, "home", lambda: tmp_path)
    dest = tmp_path / ".claude" / "skills" / "srp_existing_test"
    dest.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(install_skill, "_install_cli", lambda: None)
    monkeypatch.setattr(install_skill, "_copy_config_example", lambda: None)
    monkeypatch.setattr(install_skill, "_prompt_for_secrets", lambda: None)
    monkeypatch.setattr(install_skill, "_ensure_voicebox_secrets", lambda: None)
    monkeypatch.setattr(install_skill, "_prompt_for_runner", lambda: None)
    monkeypatch.setattr(install_skill.shutil, "copytree", lambda s, d: None)
    install_skill.run(str(dest))


def test_yt_html_write_discovered_no_unique_names(monkeypatch, tmp_path):
    """If all profile names are duplicates → no write."""
    cfg = MagicMock()
    cfg.data_dir = tmp_path
    with patch.object(yt_html, "load_active_config", return_value=cfg, create=True):
        # All same name → second skipped, but first added
        # Let's pass empty names → returns early
        yt_html._write_discovered_voicebox_profile_names([{"id": "1", "name": ""}])
    assert not (tmp_path / "voicebox_profiles.json").exists()


def test_yt_api_fetch_video_failure(monkeypatch):
    from social_research_probe.utils.core.errors import AdapterError

    with patch.object(youtube_api, "_build_client") as bc:
        bc.return_value.videos.return_value.list.return_value.execute.side_effect = RuntimeError(
            "api err"
        )
        with pytest.raises(AdapterError):
            youtube_api._fetch_video_details("k", video_ids=["v1"])


def test_yt_api_fetch_channel_failure(monkeypatch):
    from social_research_probe.utils.core.errors import AdapterError

    with patch.object(youtube_api, "_build_client") as bc:
        bc.return_value.channels.return_value.list.return_value.execute.side_effect = RuntimeError(
            "api err"
        )
        with pytest.raises(AdapterError):
            youtube_api._fetch_channel_details("k", channel_ids=["c1"])


def test_compute_normalize_with_metrics_short_metrics():
    from datetime import UTC, datetime

    from social_research_probe.platforms import RawItem

    items = [
        RawItem(
            id="1",
            url="u",
            title="t",
            author_id="a",
            author_name="A",
            published_at=datetime.now(UTC),
            metrics={},
            text_excerpt=None,
            thumbnail=None,
            extras={},
        ),
        RawItem(
            id="2",
            url="u",
            title="t",
            author_id="a",
            author_name="A",
            published_at=datetime.now(UTC),
            metrics={},
            text_excerpt=None,
            thumbnail=None,
            extras={},
        ),
    ]
    # engagement_metrics shorter than items → None aligned
    _out_items, out_em = compute_mod.normalize_with_metrics(items, [])
    assert out_em == [None, None]


def test_growth_too_few():
    assert growth.run([1.0]) == []


def test_normality_constant_returns_empty():
    assert normality.run([5.0, 5.0, 5.0]) == []


def test_normality_kurt_zero_branch():
    # kurt_verdict default branch (between thresholds)
    assert "near-normal" in normality._kurt_verdict(0.0)


def test_bayesian_with_more_features():
    # n features > some threshold
    y = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    features = {"x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]}
    out = bayesian_linear.run(y, features)
    assert isinstance(out, list)


def test_score_only_short_text():
    # Short text → various branches
    out = score("Yes.")
    assert out >= 0.0


def test_md_html_paragraph_text():
    out = markdown_to_html.md_to_html("regular paragraph text.")
    assert "<p>" in out


def test_explain_descriptive_unknown_keyword():
    # Doesn't match Mean/Median/Min/Max
    out = explain_descriptive("Sum overall: 0.5")
    assert out == ""


def test_explain_correlation_high_negative():
    out = explain_correlation("Pearson r between a and b: -0.9")
    assert "Strong tradeoff" in out


def test_filters_host_invalid_returns_none():
    # ValueError in urlparse
    out = _host("http://[malformed")
    assert out is None or out == ""


def test_html_svc_run_success(monkeypatch):

    monkeypatch.setattr(
        "social_research_probe.technologies.report_render.html.raw_html.youtube.write_html_report",
        lambda r: Path("/tmp/x.html"),
    )
    out = asyncio.run(html_svc.HtmlReportService().execute_one({"report": {}}))
    assert out.tech_results[0].success is True


def test_stats_svc_compute_with_low_confidence():
    out = _compute([{"x": 1}])
    assert out["low_confidence"] is True


def test_transcript_svc_str_input(monkeypatch):
    from social_research_probe.technologies.transcript_fetch.youtube_transcript_api import (
        YoutubeTranscriptFetch,
    )

    async def fake_exec(self, data):
        return "tx"

    monkeypatch.setattr(YoutubeTranscriptFetch, "execute", fake_exec)
    out = asyncio.run(transcript_svc.TranscriptService().execute_one("u-string"))
    assert out.input_key == "u-string"


def test_formatter_resolve_with_unwanted_marker():
    """Test placeholder marker filtering."""
    out = formatter.resolve_report_summary(
        {
            "report_summary": "(LLM synthesis unavailable here)",
            "topic": "ai",
            "platform": "youtube",
        }
    )
    assert "covers ai" in out


def test_pca_power_iteration_no_break():
    """Run iterations to exhaustion."""
    from social_research_probe.technologies.statistics import pca

    matrix = [[1.0, 0.5], [0.5, 0.5]]
    vec, _eig = pca._power_iteration(matrix, 2, iterations=2)
    assert len(vec) == 2
