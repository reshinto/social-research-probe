"""Tests for pipeline.py — requires SRP_TEST_USE_FAKE_YOUTUBE=1."""

from __future__ import annotations

import json
from datetime import UTC

import pytest

from social_research_probe.commands.parse import parse
from social_research_probe.pipeline import (
    _build_stats_summary,
    _channel_credibility,
    _enrich_query,
    _maybe_register_fake,
    _render_charts,
    _score_item,
    _zscore,
    run_research,
)


def _write_purposes(tmp_path, purposes: dict):
    """Write a valid purposes.json into tmp_path."""
    data = {
        "schema_version": 1,
        "purposes": purposes,
    }
    (tmp_path / "purposes.json").write_text(json.dumps(data), encoding="utf-8")


def test_maybe_register_fake_no_env_var(monkeypatch):
    """Without env var set, _maybe_register_fake is a no-op (covers 54->exit branch)."""
    monkeypatch.delenv("SRP_TEST_USE_FAKE_YOUTUBE", raising=False)
    _maybe_register_fake()  # should not raise or import anything


def test_enrich_query_adds_method_words():
    # "breaking" and "trending" are not stopwords so they get appended
    result = _enrich_query("AI news", "breaking trending analysis")
    assert "AI news" in result
    assert len(result) > len("AI news")


def test_enrich_query_no_extra_when_all_stopwords():
    # All words in method are stopwords — no extra added
    result = _enrich_query("topic", "the a an of for")
    assert result == "topic"


def test_channel_credibility_zero_subs():
    assert _channel_credibility(0) == 0.3
    assert _channel_credibility(None) == 0.3


def test_channel_credibility_large_subs():
    score = _channel_credibility(1_000_000)
    assert 0.0 < score <= 1.0


def test_zscore_empty():
    assert _zscore([]) == []


def test_zscore_single():
    assert _zscore([5.0]) == [0.0]


def test_zscore_two_values():
    result = _zscore([1.0, 3.0])
    assert len(result) == 2
    assert abs(result[0] + result[1]) < 1e-9  # opposite signs, sum to ~0


def test_score_item_returns_score_and_dict():
    from datetime import datetime

    from social_research_probe.platforms.base import RawItem, SignalSet, TrustHints

    item = RawItem(
        id="x",
        url="https://example.com",
        title="Test",
        author_id="ch1",
        author_name="Channel",
        published_at=datetime.now(UTC),
        metrics={"views": 1000, "likes": 50, "comments": 10},
        text_excerpt="Some text here.",
        thumbnail=None,
        extras={},
    )
    sig = SignalSet(
        views=1000,
        likes=50,
        comments=10,
        upload_date=datetime.now(UTC),
        view_velocity=100.0,
        engagement_ratio=0.06,
        comment_velocity=1.0,
        cross_channel_repetition=0.0,
        raw={},
    )
    hint = TrustHints(
        account_age_days=365,
        verified=True,
        subscriber_count=50000,
        upload_cadence_days=7.0,
        citation_markers=["https://example.com"],
    )
    score, d = _score_item(item, sig, hint, z_view_velocity=0.5, z_engagement=0.5)
    assert 0.0 <= score <= 1.0
    assert "title" in d
    assert "scores" in d


def test_run_research_returns_packet(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels for breaking news",
                "evidence_priorities": [],
            }
        },
    )
    raw = 'run-research platform:youtube "AI"->latest-news'
    cmd = parse(raw)
    packet = run_research(cmd, tmp_path, mode="cli")
    assert "topic" in packet
    assert "items_top5" in packet
    assert isinstance(packet["items_top5"], list)


def test_run_research_skill_mode_calls_emit_packet(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels for breaking news",
                "evidence_priorities": [],
            }
        },
    )
    calls = []

    def fake_emit(packet, kind):
        calls.append((packet, kind))
        raise SystemExit(0)

    monkeypatch.setattr("social_research_probe.pipeline.emit_packet", fake_emit)
    raw = 'run-research platform:youtube "AI"->latest-news'
    cmd = parse(raw)
    with pytest.raises(SystemExit):
        run_research(cmd, tmp_path, mode="skill")
    assert len(calls) == 1


def test_run_research_multi_topic(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels for breaking news",
                "evidence_priorities": [],
            }
        },
    )
    raw = 'run-research platform:youtube "AI"->latest-news;"blockchain"->latest-news'
    cmd = parse(raw)
    result = run_research(cmd, tmp_path, mode="cli")
    assert "multi" in result


def test_run_research_unknown_purpose_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    # Write purposes.json but without "nonexistent_purpose"
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels",
                "evidence_priorities": [],
            }
        },
    )
    from social_research_probe.errors import ValidationError

    raw = 'run-research platform:youtube "AI"->nonexistent_purpose'
    cmd = parse(raw)
    with pytest.raises(ValidationError):
        run_research(cmd, tmp_path, mode="cli")


def test_run_research_bad_adapter_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels",
                "evidence_priorities": [],
            }
        },
    )
    from social_research_probe.errors import ValidationError

    raw = 'run-research platform:nonexistent "AI"->latest-news'
    cmd = parse(raw)
    with pytest.raises(ValidationError):
        run_research(cmd, tmp_path, mode="cli")


def _fake_top5(n: int) -> list[dict]:
    return [
        {
            "title": f"t{i}",
            "channel": f"ch{i}",
            "url": f"https://x/{i}",
            "source_class": "secondary",
            "scores": {
                "trust": 0.5 + i * 0.05,
                "trend": 0.4 + i * 0.05,
                "opportunity": 0.6 + i * 0.05,
                "overall": 0.5 + i * 0.04,
            },
            "one_line_takeaway": "...",
        }
        for i in range(n)
    ]


def test_build_stats_summary_empty_top5():
    summary = _build_stats_summary([])
    assert summary == {"models_run": [], "highlights": [], "low_confidence": True}


def test_build_stats_summary_two_items_skips_growth():
    summary = _build_stats_summary(_fake_top5(2))
    assert summary["models_run"] == ["descriptive", "spread", "regression", "correlation"]
    assert summary["low_confidence"] is True
    assert summary["highlights"]


def test_build_stats_summary_three_items_runs_all():
    summary = _build_stats_summary(_fake_top5(3))
    assert summary["models_run"] == [
        "descriptive",
        "spread",
        "regression",
        "growth",
        "outliers",
        "correlation",
    ]
    assert summary["low_confidence"] is False


def test_render_charts_empty_returns_empty(tmp_path):
    assert _render_charts([], tmp_path) == []


def test_render_charts_writes_three_captions(tmp_path):
    captions = _render_charts(_fake_top5(3), tmp_path)
    assert len(captions) == 3
    assert (tmp_path / "charts").is_dir()
    joined = "\n".join(captions)
    assert "Bar chart" in joined
    assert "Scatter" in joined
    assert "Table" in joined or "table" in joined


def test_run_research_health_check_fails_raises(monkeypatch, tmp_path):
    """Line 97: adapter.health_check() == False raises ValidationError."""
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {
            "latest-news": {
                "method": "Track latest channels",
                "evidence_priorities": [],
            }
        },
    )
    # Patch get_adapter to return an adapter whose health_check returns False
    import social_research_probe.pipeline as pipeline_mod
    from social_research_probe.errors import ValidationError

    class FailingAdapter:
        def health_check(self):
            return False

    monkeypatch.setattr(pipeline_mod, "get_adapter", lambda name, cfg: FailingAdapter())

    raw = 'run-research platform:youtube "AI"->latest-news'
    cmd = parse(raw)
    with pytest.raises(ValidationError, match="health check"):
        run_research(cmd, tmp_path, mode="cli")


def test_build_stats_summary_single_item_runs_only_descriptive():
    summary = _build_stats_summary(_fake_top5(1))
    assert summary["models_run"] == ["descriptive"]
    assert summary["low_confidence"] is True


def test_render_charts_single_item_still_renders(tmp_path):
    captions = _render_charts(_fake_top5(1), tmp_path)
    assert len(captions) == 3


def test_stats_models_for_zero_returns_empty():
    from social_research_probe.pipeline import _stats_models_for

    assert _stats_models_for(0) == []
