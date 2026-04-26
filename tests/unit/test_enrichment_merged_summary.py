"""Tests for the parallel transcript+URL summary merge in pipeline.enrichment."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from social_research_probe.pipeline import enrichment


@pytest.fixture
def _enable_summary_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("SRP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SRP_DISABLE_CACHE", raising=False)
    return tmp_path


@pytest.mark.asyncio
async def test_url_based_summary_returns_none_when_flag_off(monkeypatch):
    class _Cfg:
        def allows(self, *, stage=None, service=None, technology=None):
            return service != "media_url_summary"

    with patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()):
        out = await enrichment._url_based_summary("https://y/1", word_limit=100)
    assert out is None


@pytest.mark.asyncio
async def test_url_based_summary_returns_none_when_no_capable_runner(monkeypatch):
    class _Cfg:
        def allows(self, **kwargs):
            return True

    with (
        patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()),
        patch(
            "social_research_probe.pipeline.enrichment._first_media_url_runner",
            return_value=None,
        ),
    ):
        out = await enrichment._url_based_summary("https://y/1", word_limit=100)
    assert out is None


@pytest.mark.asyncio
async def test_merge_or_pick_returns_text_only_when_url_missing():
    class _ItemDict(dict):
        pass

    item = _ItemDict()
    out = await enrichment._merge_or_pick(item, "text-summary", None, "transcript", 100, 0.4)
    assert out == "text-summary"


@pytest.mark.asyncio
async def test_merge_or_pick_returns_url_only_when_text_missing():
    item: dict = {}
    out = await enrichment._merge_or_pick(item, None, "url-summary", "", 100, 0.4)
    assert out == "url-summary"
    assert item["url_summary"] == "url-summary"


@pytest.mark.asyncio
async def test_merge_or_pick_falls_back_to_transcript_excerpt():
    item: dict = {}
    long_text = " ".join(["word"] * 200)
    out = await enrichment._merge_or_pick(item, None, None, long_text, 100, 0.4)
    assert out is not None
    assert out.endswith("...")


@pytest.mark.asyncio
async def test_merge_or_pick_records_divergence_when_both_present():
    class _Cfg:
        def allows(self, *, stage=None, service=None, technology=None):
            return service not in {"merged_summary", "llm"}

    item: dict = {"title": "vid"}
    text = "alpha beta gamma delta"
    url = "epsilon zeta eta theta"
    with patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()):
        out = await enrichment._merge_or_pick(item, text, url, "", 100, 0.4)
    assert out == text
    assert item["summary_divergence"] == 1.0
    assert item["url_summary"] == url


@pytest.mark.asyncio
async def test_merge_or_pick_invokes_reconcile_when_enabled():
    class _Cfg:
        def allows(self, **kwargs):
            return True

    async def _fake_reconcile(*_a, **_k):
        return "RECONCILED"

    item: dict = {"title": "vid"}
    with (
        patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()),
        patch(
            "social_research_probe.pipeline.enrichment._reconcile_summaries",
            side_effect=_fake_reconcile,
        ),
    ):
        out = await enrichment._merge_or_pick(item, "text", "url", "", 100, 0.4)
    assert out == "RECONCILED"
    assert "summary_divergence" in item


@pytest.mark.asyncio
async def test_url_based_summary_returns_none_in_fast_mode(monkeypatch):
    """Fast mode skips the URL summary path entirely — no runner call."""
    monkeypatch.setenv("SRP_FAST_MODE", "1")
    called = [0]

    def _runner():
        called[0] += 1
        return None

    with patch(
        "social_research_probe.pipeline.enrichment._first_media_url_runner", side_effect=_runner
    ):
        out = await enrichment._url_based_summary("https://y/1", word_limit=100)

    assert out is None
    assert called[0] == 0


@pytest.mark.asyncio
async def test_merge_or_pick_does_not_reconcile_in_fast_mode(monkeypatch):
    """Fast mode disables reconciliation even when summaries diverge."""
    monkeypatch.setenv("SRP_FAST_MODE", "1")

    class _Cfg:
        def allows(self, **kwargs):
            return True

    async def _fake_reconcile(*_a, **_k):
        raise AssertionError("reconcile must not be called in fast mode")

    item: dict = {"title": "vid"}
    with (
        patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()),
        patch(
            "social_research_probe.pipeline.enrichment._reconcile_summaries",
            side_effect=_fake_reconcile,
        ),
    ):
        out = await enrichment._merge_or_pick(item, "text", "url", "", 100, 0.4)

    assert out == "text"


@pytest.mark.asyncio
async def test_merge_or_pick_skips_reconcile_when_divergence_below_threshold():
    """Reconciliation is expensive; skip it when the two summaries already agree."""

    class _Cfg:
        def allows(self, **kwargs):
            return True

    reconcile_calls: list = []

    async def _fake_reconcile(*_a, **_k):
        reconcile_calls.append(1)
        return "RECONCILED"

    item: dict = {"title": "vid"}
    shared = "alpha beta gamma delta epsilon"
    with (
        patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()),
        patch(
            "social_research_probe.pipeline.enrichment._reconcile_summaries",
            side_effect=_fake_reconcile,
        ),
    ):
        out = await enrichment._merge_or_pick(item, shared, shared, "", 100, 0.4)
    assert out == shared
    assert reconcile_calls == []
    assert item["summary_divergence"] == 0.0


@pytest.mark.asyncio
async def test_url_based_summary_uses_cache_on_second_call(_enable_summary_cache):
    """Second call on same video_id reuses the cached URL summary — no runner call."""

    class _Cfg:
        def allows(self, **kwargs):
            return True

    class _Runner:
        def __init__(self):
            self.calls = 0

        async def summarize_media(self, url, word_limit):
            self.calls += 1
            return "URL-SUMMARY"

    runner = _Runner()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    with (
        patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()),
        patch(
            "social_research_probe.pipeline.enrichment._first_media_url_runner",
            return_value=runner,
        ),
    ):
        first = await enrichment._url_based_summary(url, word_limit=100)
        second = await enrichment._url_based_summary(url, word_limit=100)

    assert first == second == "URL-SUMMARY"
    assert runner.calls == 1


@pytest.mark.asyncio
async def test_cached_text_summary_caches_by_video_and_prompt(_enable_summary_cache):
    """Same prompt for the same video hits the cache; no second LLM call."""
    llm_calls = [0]

    async def _fake_multi(prompt, task):
        llm_calls[0] += 1
        return "TEXT-SUMMARY"

    item = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    with patch(
        "social_research_probe.pipeline.enrichment.multi_llm_prompt", side_effect=_fake_multi
    ):
        first = await enrichment._cached_text_summary(item, "prompt-body", "task")
        second = await enrichment._cached_text_summary(item, "prompt-body", "task")

    assert first == second == "TEXT-SUMMARY"
    assert llm_calls[0] == 1


@pytest.mark.asyncio
async def test_cached_text_summary_falls_through_for_non_youtube(_enable_summary_cache):
    """Items without a parseable video_id bypass the cache entirely."""
    llm_calls = [0]

    async def _fake_multi(prompt, task):
        llm_calls[0] += 1
        return "SUM"

    item = {"url": "https://vimeo.com/123"}
    with patch(
        "social_research_probe.pipeline.enrichment.multi_llm_prompt", side_effect=_fake_multi
    ):
        await enrichment._cached_text_summary(item, "p", "t")
        await enrichment._cached_text_summary(item, "p", "t")

    assert llm_calls[0] == 2


@pytest.mark.asyncio
async def test_reconcile_summaries_returns_none_without_caching_when_llm_fails(
    _enable_summary_cache,
):
    """Falsy LLM output (None/empty) is not cached so a later retry can succeed."""

    async def _fake_multi(prompt, task):
        return None

    with patch(
        "social_research_probe.pipeline.enrichment.multi_llm_prompt", side_effect=_fake_multi
    ):
        out = await enrichment._reconcile_summaries(
            title="vid",
            channel="ch",
            transcript_summary="text",
            url_summary="url",
            word_limit=100,
        )
    assert out is None


@pytest.mark.asyncio
async def test_cached_text_summary_returns_none_without_caching_when_llm_fails(
    _enable_summary_cache,
):
    """Falsy LLM output is not cached — next call must hit the LLM again."""
    call_count = [0]

    async def _fake_multi(prompt, task):
        call_count[0] += 1
        return None

    item = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    with patch(
        "social_research_probe.pipeline.enrichment.multi_llm_prompt", side_effect=_fake_multi
    ):
        first = await enrichment._cached_text_summary(item, "prompt", "task")
        second = await enrichment._cached_text_summary(item, "prompt", "task")

    assert first is None
    assert second is None
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_reconcile_summaries_caches_by_content(_enable_summary_cache):
    """Reconciliation is memoised on the (title, text, url) inputs."""
    llm_calls = [0]

    async def _fake_multi(prompt, task):
        llm_calls[0] += 1
        return "MERGED"

    with patch(
        "social_research_probe.pipeline.enrichment.multi_llm_prompt", side_effect=_fake_multi
    ):
        first = await enrichment._reconcile_summaries(
            title="vid",
            channel="ch",
            transcript_summary="text",
            url_summary="url",
            word_limit=100,
        )
        second = await enrichment._reconcile_summaries(
            title="vid",
            channel="ch",
            transcript_summary="text",
            url_summary="url",
            word_limit=100,
        )

    assert first == second == "MERGED"
    assert llm_calls[0] == 1


def test_first_media_url_runner_skips_unhealthy():
    class _Cfg:
        llm_runner = "gemini"

    class _R:
        supports_media_url = True

        def health_check(self):
            return False

    with (
        patch("social_research_probe.llm.registry.get_runner", return_value=_R()),
    ):
        assert enrichment._first_media_url_runner(_Cfg()) is None


def test_first_media_url_runner_loads_active_config_when_cfg_omitted():
    class _Cfg:
        llm_runner = "gemini"

    class _Runner:
        supports_media_url = True

        def health_check(self):
            return True

    with (
        patch("social_research_probe.pipeline.enrichment.load_active_config", return_value=_Cfg()),
        patch("social_research_probe.llm.registry.get_runner", return_value=_Runner()),
    ):
        runner = enrichment._first_media_url_runner()

    assert runner is not None
    assert runner.supports_media_url is True


def test_first_media_url_runner_skips_runners_without_capability():
    class _Cfg:
        llm_runner = "claude"

    class _NotCapable:
        supports_media_url = False

        def health_check(self):
            return True

    with patch("social_research_probe.llm.registry.get_runner", return_value=_NotCapable()):
        assert enrichment._first_media_url_runner(_Cfg()) is None


def test_first_media_url_runner_returns_none_when_health_check_raises():
    class _Cfg:
        llm_runner = "gemini"

    class _Runner:
        supports_media_url = True

        def health_check(self):
            raise RuntimeError("boom")

    with patch("social_research_probe.llm.registry.get_runner", return_value=_Runner()):
        assert enrichment._first_media_url_runner(_Cfg()) is None


def test_first_media_url_runner_returns_none_when_llm_runner_disabled():
    class _Cfg:
        llm_runner = "none"

    with patch("social_research_probe.llm.registry.get_runner") as get_runner:
        assert enrichment._first_media_url_runner(_Cfg()) is None
    get_runner.assert_not_called()


def test_first_media_url_runner_returns_none_when_llm_service_gate_disabled():
    class _Cfg:
        llm_runner = "gemini"

        def allows(self, *, stage=None, service=None, technology=None):
            return service != "llm"

    with patch("social_research_probe.llm.registry.get_runner") as get_runner:
        assert enrichment._first_media_url_runner(_Cfg()) is None
    get_runner.assert_not_called()


def test_first_media_url_runner_returns_none_when_runner_technology_disabled():
    class _Cfg:
        llm_runner = "gemini"

        def allows(self, *, stage=None, service=None, technology=None):
            return technology != "gemini"

    with patch("social_research_probe.llm.registry.get_runner") as get_runner:
        assert enrichment._first_media_url_runner(_Cfg()) is None
    get_runner.assert_not_called()


@pytest.mark.asyncio
async def test_url_based_summary_does_not_use_other_runner_when_llm_runner_disabled(monkeypatch):
    class _Cfg:
        llm_runner = "none"

        def allows(self, **kwargs):
            return True

    async def _unexpected_summary(url, word_limit):
        raise AssertionError("summarize_media must not run when llm.runner is disabled")

    class _Runner:
        summarize_media = _unexpected_summary

    monkeypatch.setattr(
        "social_research_probe.pipeline.enrichment.load_active_config",
        lambda: _Cfg(),
    )
    with patch(
        "social_research_probe.llm.registry.get_runner",
        return_value=_Runner(),
    ) as get_runner:
        out = await enrichment._url_based_summary("https://y/1", word_limit=100)

    assert out is None
    get_runner.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_transcript_with_fallback_skips_transcript_api_when_technology_disabled():
    class _Cfg:
        def allows(self, *, stage=None, service=None, technology=None):
            if service == "transcripts":
                return True
            if technology == "youtube_transcript_api":
                return False
            if technology == "whisper":
                return True
            return True

    def _fetch_transcript(url):
        raise AssertionError("caption fetch should be skipped")

    def _fetch_transcript_whisper(url):
        return "whisper transcript"

    text = await enrichment._fetch_transcript_with_fallback(
        {"url": "https://example.com/v/1"},
        _fetch_transcript,
        _fetch_transcript_whisper,
        asyncio.Semaphore(1),
        cfg=_Cfg(),
    )

    assert text == "whisper transcript"
