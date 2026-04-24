"""Tests for pipeline.py — requires SRP_TEST_USE_FAKE_YOUTUBE=1."""

from __future__ import annotations

import json
from datetime import UTC
from typing import ClassVar
from unittest.mock import AsyncMock

import pytest
from social_research_probe.errors import ValidationError
from social_research_probe.pipeline.charts import _render_charts
from social_research_probe.pipeline.corroboration import _corroborate_top_n
from social_research_probe.pipeline.enrichment import _enrich_top_n_with_transcripts
from social_research_probe.pipeline.scoring import (
    _channel_credibility,
    _enrich_query,
    _score_item,
    _zscore,
)
from social_research_probe.pipeline.stats import _build_stats_summary, _stats_models_for
from social_research_probe.pipeline.svs import _build_svs

from social_research_probe.commands.parse import parse
from social_research_probe.pipeline.orchestrator import (
    _available_backends,
    _maybe_register_fake,
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


def test_score_item_custom_weights_shift_overall():
    from datetime import datetime

    from social_research_probe.platforms.base import RawItem, SignalSet, TrustHints

    item = RawItem(
        id="x",
        url="https://example.com",
        title="T",
        author_id="c",
        author_name="C",
        published_at=datetime.now(UTC),
        metrics={"views": 100, "likes": 1, "comments": 0},
        text_excerpt="",
        thumbnail=None,
        extras={},
    )
    sig = SignalSet(
        views=100,
        likes=1,
        comments=0,
        upload_date=datetime.now(UTC),
        view_velocity=1.0,
        engagement_ratio=0.01,
        comment_velocity=0.0,
        cross_channel_repetition=0.0,
        raw={},
    )
    hint = TrustHints(
        account_age_days=0,
        verified=False,
        subscriber_count=0,
        upload_cadence_days=0.0,
        citation_markers=[],
    )
    default_score, _ = _score_item(item, sig, hint, 0.0, 0.0)
    trust_only, _ = _score_item(
        item, sig, hint, 0.0, 0.0, {"trust": 1.0, "trend": 0.0, "opportunity": 0.0}
    )
    assert default_score != trust_only


def test_resolve_scoring_weights_purpose_overrides_config():
    from social_research_probe.purposes.merge import MergedPurpose

    from social_research_probe.pipeline.orchestrator import _resolve_scoring_weights

    class _Cfg:
        raw: ClassVar[dict] = {
            "scoring": {"weights": {"trust": 0.6, "trend": 0.2, "opportunity": 0.2}}
        }

    merged = MergedPurpose(
        names=("p",),
        method="m",
        evidence_priorities=(),
        scoring_overrides={"trust": 0.9},
    )
    w = _resolve_scoring_weights(_Cfg(), merged)
    assert w["trust"] == 0.9
    assert w["trend"] == 0.2
    assert w["opportunity"] == 0.2


def test_resolve_scoring_weights_defaults_when_empty():
    from social_research_probe.purposes.merge import MergedPurpose
    from social_research_probe.scoring.combine import DEFAULT_WEIGHTS

    from social_research_probe.pipeline.orchestrator import _resolve_scoring_weights

    class _Cfg:
        raw: ClassVar[dict] = {"scoring": {"weights": {}}}

    merged = MergedPurpose(names=("p",), method="m", evidence_priorities=())
    assert _resolve_scoring_weights(_Cfg(), merged) == DEFAULT_WEIGHTS


async def test_run_research_returns_packet(monkeypatch, tmp_path):
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
    packet = await run_research(cmd, tmp_path)
    assert "topic" in packet
    assert "items_top_n" in packet
    assert isinstance(packet["items_top_n"], list)


async def test_run_research_degrades_when_fetch_stage_disabled(monkeypatch, tmp_path):
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
    (tmp_path / "config.toml").write_text(
        "[stages]\nfetch = false\n",
        encoding="utf-8",
    )
    raw = 'run-research platform:youtube "AI"->latest-news'
    packet = await run_research(parse(raw), tmp_path)
    assert packet["topic"] == "AI"
    assert packet["items_top_n"] == []
    assert packet["chart_captions"] == []


async def test_run_research_does_not_emit_or_exit(monkeypatch, tmp_path):
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
    packet = await run_research(cmd, tmp_path)
    assert packet["topic"] == "AI"
    assert "compiled_synthesis" not in packet
    assert "opportunity_analysis" not in packet


async def test_run_research_multi_topic(monkeypatch, tmp_path):
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
    result = await run_research(cmd, tmp_path)
    assert "multi" in result


async def test_run_research_unknown_purpose_raises(monkeypatch, tmp_path):
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

    raw = 'run-research platform:youtube "AI"->nonexistent_purpose'
    cmd = parse(raw)
    with pytest.raises(ValidationError):
        await run_research(cmd, tmp_path)


async def test_run_research_bad_adapter_raises(monkeypatch, tmp_path):
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

    raw = 'run-research platform:nonexistent "AI"->latest-news'
    cmd = parse(raw)
    with pytest.raises(ValidationError):
        await run_research(cmd, tmp_path)


def _fake_top_n(n: int) -> list[dict]:
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
            "features": {
                "view_velocity": 100.0 + i * 10,
                "engagement_ratio": 0.02 + i * 0.005,
                "age_days": 1.0 + i,
                "subscriber_count": 1000.0 + i * 500,
            },
            "one_line_takeaway": "...",
        }
        for i in range(n)
    ]


def test_build_stats_summary_empty_top_n():
    summary = _build_stats_summary([])
    assert summary == {"models_run": [], "highlights": [], "low_confidence": True}


def test_build_stats_summary_two_items_skips_growth():
    summary = _build_stats_summary(_fake_top_n(2))
    assert summary["models_run"] == [
        "descriptive",
        "spread",
        "regression",
        "correlation",
        "spearman",
        "mann_whitney",
        "welch_t",
    ]
    assert summary["low_confidence"] is True
    assert summary["highlights"]


def test_build_stats_summary_three_items_runs_all_models_but_low_confidence():
    summary = _build_stats_summary(_fake_top_n(3))
    assert summary["models_run"] == [
        "descriptive",
        "spread",
        "regression",
        "growth",
        "outliers",
        "correlation",
        "spearman",
        "mann_whitney",
        "welch_t",
    ]
    assert summary["low_confidence"] is True


def test_build_stats_summary_eight_items_clears_low_confidence():
    summary = _build_stats_summary(_fake_top_n(8))
    assert summary["low_confidence"] is False


def test_render_charts_empty_returns_empty(tmp_path):
    assert _render_charts([], tmp_path) == []


def test_render_charts_writes_full_chart_suite(tmp_path):
    captions = _render_charts(_fake_top_n(3), tmp_path)
    assert len(captions) == 10
    assert (tmp_path / "charts").is_dir()
    joined = "\n".join(captions)
    assert "Bar chart" in joined
    assert "Line chart" in joined
    assert "Histogram" in joined
    assert "Regression" in joined
    assert "Correlation heatmap" in joined
    assert "Residuals" in joined
    assert "Table" in joined or "table" in joined


async def test_run_research_health_check_fails_raises(monkeypatch, tmp_path):
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
    import social_research_probe.pipeline.orchestrator as orchestrator_mod

    class FailingAdapter:
        def health_check(self):
            return False

    monkeypatch.setattr(orchestrator_mod, "get_adapter", lambda name, cfg: FailingAdapter())

    raw = 'run-research platform:youtube "AI"->latest-news'
    cmd = parse(raw)
    with pytest.raises(ValidationError, match="health check"):
        await run_research(cmd, tmp_path)


def test_build_stats_summary_single_item_runs_only_descriptive():
    summary = _build_stats_summary(_fake_top_n(1))
    assert summary["models_run"] == ["descriptive"]
    assert summary["low_confidence"] is True


def test_render_charts_single_item_still_renders(tmp_path):
    captions = _render_charts(_fake_top_n(1), tmp_path)
    assert len(captions) == 10


def test_stats_models_for_zero_returns_empty():
    assert _stats_models_for(0) == []


class TestEnrichTopNWithTranscripts:
    async def test_stores_transcript_and_summary_when_available(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.extract.fetch_transcript",
            lambda url: "first  line\nsecond  line " * 200,
        )
        monkeypatch.setattr(
            "social_research_probe.pipeline.enrichment.multi_llm_prompt",
            AsyncMock(return_value="Multi-LLM generated summary."),
        )
        items = [{"url": "https://x/1", "title": "T", "channel": "C", "one_line_takeaway": "desc"}]
        await _enrich_top_n_with_transcripts(items)
        assert "transcript" in items[0]
        assert len(items[0]["transcript"]) <= 6000
        assert items[0]["one_line_takeaway"] == "Multi-LLM generated summary."

    async def test_falls_back_to_transcript_excerpt_when_llm_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.extract.fetch_transcript",
            lambda url: "some transcript content",
        )
        monkeypatch.setattr(
            "social_research_probe.pipeline.enrichment.multi_llm_prompt",
            AsyncMock(return_value=None),
        )
        items = [
            {"url": "https://x/1", "title": "T", "channel": "C", "one_line_takeaway": "keep me"}
        ]
        await _enrich_top_n_with_transcripts(items)
        assert "transcript" in items[0]
        assert items[0]["one_line_takeaway"] == "some transcript content"

    async def test_no_transcript_key_when_fetch_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.extract.fetch_transcript",
            lambda url: None,
        )
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
            lambda url: None,
        )
        items = [{"url": "https://x/1", "one_line_takeaway": "keep me"}]
        await _enrich_top_n_with_transcripts(items)
        assert "transcript" not in items[0]
        assert items[0]["one_line_takeaway"] == "keep me"

    async def test_silently_recovers_from_extractor_exception(self, monkeypatch):
        def boom(url):
            raise RuntimeError("network gone")

        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.extract.fetch_transcript",
            boom,
        )
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
            lambda url: None,
        )
        items = [{"url": "https://x/1", "one_line_takeaway": "still here"}]
        await _enrich_top_n_with_transcripts(items)
        assert "transcript" not in items[0]
        assert items[0]["one_line_takeaway"] == "still here"

    async def test_uses_whisper_when_caption_fetch_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.extract.fetch_transcript",
            lambda url: None,
        )
        monkeypatch.setattr(
            "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
            lambda url: "Whisper-produced transcript text.",
        )
        monkeypatch.setattr(
            "social_research_probe.pipeline.enrichment.multi_llm_prompt",
            AsyncMock(return_value="Summary from whisper transcript."),
        )
        items = [{"url": "https://x/1", "title": "T", "channel": "C", "one_line_takeaway": "orig"}]
        await _enrich_top_n_with_transcripts(items)
        assert items[0]["transcript"] == "Whisper-produced transcript text."
        assert items[0]["one_line_takeaway"] == "Summary from whisper transcript."


async def test_enrich_top_n_skips_when_transcript_is_whitespace_only(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.extract.fetch_transcript",
        lambda url: "   \n   ",
    )
    monkeypatch.setattr(
        "social_research_probe.platforms.youtube.whisper_transcript.fetch_transcript_whisper",
        lambda url: None,
    )
    items = [{"url": "https://x", "one_line_takeaway": "orig"}]
    await _enrich_top_n_with_transcripts(items)
    assert "transcript" not in items[0]
    assert items[0]["one_line_takeaway"] == "orig"


async def test_run_research_respects_enrich_top_n_config(monkeypatch, tmp_path):
    """adapter_config.enrich_top_n=2 limits items_top_n to 2 entries instead of 5."""
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {"latest-news": {"method": "Track latest channels", "evidence_priorities": []}},
    )
    cmd = parse('run-research platform:youtube "AI"->latest-news')
    packet = await run_research(cmd, tmp_path, adapter_config={"enrich_top_n": 2})
    assert len(packet["items_top_n"]) == 2


async def test_run_research_default_enrich_top_n_is_5(monkeypatch, tmp_path):
    """Without enrich_top_n override, items_top_n keeps the 5-item default."""
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {"latest-news": {"method": "Track latest channels", "evidence_priorities": []}},
    )
    cmd = parse('run-research platform:youtube "AI"->latest-news')
    packet = await run_research(cmd, tmp_path)
    assert len(packet["items_top_n"]) == 5


async def test_run_research_skips_transcript_enrich_when_disabled(monkeypatch, tmp_path):
    """adapter_config.fetch_transcripts=False skips the _enrich_top_n call."""
    monkeypatch.setenv("SRP_TEST_USE_FAKE_YOUTUBE", "1")
    _write_purposes(
        tmp_path,
        {"latest-news": {"method": "Track latest channels", "evidence_priorities": []}},
    )
    called = []
    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment._enrich_top_n_with_transcripts",
        AsyncMock(side_effect=called.append),
    )
    cmd = parse('run-research platform:youtube "AI"->latest-news')
    await run_research(cmd, tmp_path, adapter_config={"fetch_transcripts": False})
    assert called == []


# ---------------------------------------------------------------------------
# _available_backends
# ---------------------------------------------------------------------------


def test_available_backends_returns_healthy_ones(monkeypatch, tmp_path):
    """Backend names whose health_check() returns True are included."""
    import social_research_probe.corroboration.registry as reg

    class _HealthyBackend:
        def health_check(self) -> bool:
            return True

    class _SickBackend:
        def health_check(self) -> bool:
            return False

    def fake_get(name: str):
        return _HealthyBackend() if name == "exa" else _SickBackend()

    monkeypatch.setattr(reg, "get_backend", fake_get)
    result = _available_backends(tmp_path)
    assert result == ["exa"]


def test_available_backends_returns_empty_when_all_unhealthy(monkeypatch, tmp_path):
    """Returns an empty list when no backends pass health_check()."""
    import social_research_probe.corroboration.registry as reg

    class _SickBackend:
        def health_check(self) -> bool:
            return False

    monkeypatch.setattr(reg, "get_backend", lambda _name: _SickBackend())
    assert _available_backends(tmp_path) == []


def test_available_backends_swallows_validation_error(monkeypatch, tmp_path):
    """ValidationError from get_backend is silently skipped."""
    import social_research_probe.corroboration.registry as reg

    monkeypatch.setattr(
        reg, "get_backend", lambda _name: (_ for _ in ()).throw(ValidationError("bad"))
    )
    assert _available_backends(tmp_path) == []


def test_available_backends_honors_specific_backend_config(monkeypatch, tmp_path):
    """A specific configured backend bypasses auto discovery."""
    import social_research_probe.corroboration.registry as reg

    class _Cfg:
        corroboration_backend = "llm_search"

    class _Backend:
        def health_check(self) -> bool:
            return True

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator.Config.load", lambda data_dir: _Cfg()
    )
    monkeypatch.setattr(reg, "get_backend", lambda name: _Backend())
    assert _available_backends(tmp_path) == ["llm_search"]


def test_available_backends_returns_empty_when_config_disables_it(monkeypatch, tmp_path):
    """backend=none disables corroboration even if backends would be healthy."""

    class _Cfg:
        corroboration_backend = "none"

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator.Config.load", lambda data_dir: _Cfg()
    )
    assert _available_backends(tmp_path) == []


def test_available_backends_returns_empty_when_stage_disables_corroboration(monkeypatch, tmp_path):
    class _Cfg:
        corroboration_backend = "auto"

        def stage_enabled(self, name: str) -> bool:
            return name != "corroborate"

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator.Config.load", lambda data_dir: _Cfg()
    )
    assert _available_backends(tmp_path) == []


def test_available_backends_returns_empty_when_service_disables_corroboration(
    monkeypatch, tmp_path
):
    class _Cfg:
        corroboration_backend = "auto"

        def service_enabled(self, name: str) -> bool:
            return name != "corroboration"

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator.Config.load", lambda data_dir: _Cfg()
    )
    assert _available_backends(tmp_path) == []


def test_available_backends_skips_backend_when_technology_is_disabled(monkeypatch, tmp_path):
    import social_research_probe.corroboration.registry as reg

    class _Cfg:
        corroboration_backend = "exa"

        def technology_enabled(self, name: str) -> bool:
            return name != "exa"

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator.Config.load", lambda data_dir: _Cfg()
    )
    monkeypatch.setattr(
        reg,
        "get_backend",
        lambda name: (_ for _ in ()).throw(AssertionError("backend lookup should be skipped")),
    )
    assert _available_backends(tmp_path) == []


def test_available_backends_skips_llm_search_when_llm_service_is_disabled(monkeypatch, tmp_path):
    import social_research_probe.corroboration.registry as reg

    class _Cfg:
        corroboration_backend = "llm_search"

        def technology_enabled(self, name: str) -> bool:
            return True

        def service_enabled(self, name: str) -> bool:
            return name != "llm"

    monkeypatch.setattr(
        "social_research_probe.pipeline.orchestrator.Config.load", lambda data_dir: _Cfg()
    )
    monkeypatch.setattr(
        reg,
        "get_backend",
        lambda name: (_ for _ in ()).throw(AssertionError("llm_search should be skipped")),
    )
    assert _available_backends(tmp_path) == []


# ---------------------------------------------------------------------------
# _corroborate_top_n
# ---------------------------------------------------------------------------


async def test_corroborate_top_n_calls_corroborate_claim_for_each_item(monkeypatch, tmp_path):
    """Each top-N item produces one corroborate_claim call."""
    calls: list[str] = []

    async def fake_corroborate(claim, backends):
        calls.append(claim.text)
        return {
            "claim_text": claim.text,
            "results": [],
            "aggregate_verdict": "supported",
            "aggregate_confidence": 0.8,
        }

    monkeypatch.setattr(
        "social_research_probe.corroboration.host.corroborate_claim",
        fake_corroborate,
    )
    items = [
        {"title": f"Title {i}", "one_line_takeaway": "summary", "url": f"https://x/{i}"}
        for i in range(3)
    ]
    results = await _corroborate_top_n(items, ["exa"])
    assert len(results) == 3
    assert all(r.get("aggregate_verdict") == "supported" for r in results)


async def test_corroborate_top_n_tolerates_backend_failure(monkeypatch, tmp_path):
    """A backend exception for one item returns an empty dict for that item."""

    async def fake_corroborate(claim, backends):
        if "bad" in claim.text:
            raise RuntimeError("network error")
        return {"aggregate_verdict": "supported", "aggregate_confidence": 0.9, "results": []}

    monkeypatch.setattr(
        "social_research_probe.corroboration.host.corroborate_claim",
        fake_corroborate,
    )
    items = [
        {"title": "Good title", "one_line_takeaway": "ok", "url": "https://x/1"},
        {"title": "bad title", "one_line_takeaway": "fail", "url": "https://x/2"},
    ]
    results = await _corroborate_top_n(items, ["exa"])
    assert len(results) == 2
    # The good item has a verdict; the bad item got an empty fallback dict
    assert results[0].get("aggregate_verdict") == "supported"
    assert results[1] == {}


# ---------------------------------------------------------------------------
# _build_svs
# ---------------------------------------------------------------------------


def _make_item(source_class: str = "secondary", trust: float = 0.7) -> dict:
    return {
        "source_class": source_class,
        "scores": {"trust": trust},
    }


def test_build_svs_with_corroboration_counts_verdicts():
    items = [_make_item(), _make_item(), _make_item()]
    corr = [
        {"aggregate_verdict": "supported", "aggregate_confidence": 0.8, "results": [{}]},
        {"aggregate_verdict": "inconclusive", "aggregate_confidence": 0.5, "results": [{}]},
        {"aggregate_verdict": "refuted", "aggregate_confidence": 0.3, "results": [{}]},
    ]
    svs = _build_svs(items, corr, ["exa"])
    assert svs["validated"] == 1
    assert svs["partially"] == 2
    assert svs["unverified"] == 0
    assert "auto-corroborated" in svs["notes"]
    assert "exa" in svs["notes"]


def test_build_svs_without_corroboration_uses_defaults():
    items = [_make_item(), _make_item()]
    svs = _build_svs(items, [], [])
    assert svs["validated"] == 0
    assert svs["unverified"] == 2
    assert "corroboration not run" in svs["notes"]


def test_build_svs_counts_source_classes_and_low_trust():
    items = [
        _make_item("primary", 0.7),
        _make_item("secondary", 0.3),
        _make_item("commentary", 0.8),
    ]
    svs = _build_svs(items, [], [])
    assert svs["primary"] == 1
    assert svs["secondary"] == 1
    assert svs["commentary"] == 1
    assert svs["low_trust"] == 1  # only the 0.3 trust item
