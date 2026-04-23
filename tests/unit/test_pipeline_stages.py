"""Direct unit tests for the explicit stage executor and cache payload helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from social_research_probe.pipeline import stages as stage_mod
from social_research_probe.platforms.base import FetchLimits, RawItem, SignalSet, TrustHints

_NOW = datetime(2026, 1, 2, tzinfo=UTC)


class _Cfg:
    def __init__(
        self,
        *,
        stages: dict[str, bool] | None = None,
        services: dict[str, bool] | None = None,
        technologies: dict[str, bool] | None = None,
        corroboration_backend: str = "auto",
        llm_runner: str = "claude",
    ) -> None:
        self._stages = stages or {}
        self._services = services or {}
        self._technologies = technologies or {}
        self.corroboration_backend = corroboration_backend
        self.llm_runner = llm_runner

    def stage_enabled(self, name: str) -> bool:
        return self._stages.get(name, True)

    def service_enabled(self, name: str) -> bool:
        return self._services.get(name, True)

    def technology_enabled(self, name: str) -> bool:
        return self._technologies.get(name, True)


class _Adapter:
    def __init__(self, *, subscriber_count: int | None = 1000) -> None:
        self.subscriber_count = subscriber_count

    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        assert topic
        assert isinstance(limits, FetchLimits)
        return [_raw_item()]

    async def enrich(self, items: list[RawItem]) -> list[RawItem]:
        return items

    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:
        assert items
        return [_signal()]

    def trust_hints(self, item: RawItem) -> TrustHints:
        return TrustHints(
            account_age_days=365,
            verified=True,
            subscriber_count=self.subscriber_count,
            upload_cadence_days=7.0,
            citation_markers=[],
        )

    def url_normalize(self, url: str) -> str:
        return url


def _raw_item(
    *,
    published_at: datetime | None = _NOW,
    text_excerpt: str | None = "Short excerpt",
) -> RawItem:
    return RawItem(
        id="item-1",
        url="https://example.com/v/1",
        title="Video 1",
        author_id="chan-1",
        author_name="Channel 1",
        published_at=published_at,  # type: ignore[arg-type]
        metrics={"views": 1000},
        text_excerpt=text_excerpt,
        thumbnail=None,
        extras={},
    )


def _signal(
    *,
    upload_date: datetime | None = _NOW,
    view_velocity: float | None = 10.0,
    engagement_ratio: float | None = 0.2,
) -> SignalSet:
    return SignalSet(
        views=1000,
        likes=100,
        comments=10,
        upload_date=upload_date,
        view_velocity=view_velocity,
        engagement_ratio=engagement_ratio,
        comment_velocity=1.0,
        cross_channel_repetition=0.0,
        raw={},
    )


def _ctx(
    tmp_path,
    *,
    cfg: _Cfg | None = None,
    adapter: _Adapter | None = None,
    outputs: dict[str, dict[str, object]] | None = None,
    platform: str = "youtube",
    fetch_transcripts: bool = True,
    backends: list[str] | None = None,
):
    return stage_mod.StageExecutionContext(
        cfg=cfg or _Cfg(),
        cmd=SimpleNamespace(platform=platform),
        data_dir=tmp_path,
        adapter=adapter or _Adapter(),
        platform_config={"enrich_top_n": 1, "fetch_transcripts": fetch_transcripts},
        limits=FetchLimits(max_items=1, recency_days=7),
        topic="AI",
        purpose_names=["latest-news"],
        search_topic="AI latest",
        scoring_weights={"trust": 0.4, "trend": 0.3, "opportunity": 0.3},
        timings={"stage_timings": []},
        outputs=outputs or {},
        corroboration_backends=backends,
    )


def test_payload_helpers_roundtrip_dates_and_missing_values():
    item_payload = {
        "id": "x",
        "url": "https://example.com/x",
        "title": "Title",
        "author_id": "a",
        "author_name": "Author",
    }
    signal_payload = {}

    restored_item = stage_mod._raw_item_from_dict(item_payload)
    restored_signal = stage_mod._signal_from_dict(signal_payload)

    assert stage_mod._dt_from_str(None) is None
    assert restored_item.published_at is not None
    assert restored_signal.upload_date is None
    assert restored_signal.raw == {}


def test_fallback_scored_items_uses_defaults_for_missing_values():
    adapter = _Adapter(subscriber_count=None)
    output = stage_mod._fallback_scored_items(
        [_raw_item(published_at=None, text_excerpt=None)],  # type: ignore[arg-type]
        [_signal(upload_date=None, view_velocity=None, engagement_ratio=None)],
        adapter,
        top_n=1,
    )

    scored = output["all_scored"][0]
    assert scored["features"]["age_days"] == 30.0
    assert scored["features"]["subscriber_count"] == 0.0
    assert scored["one_line_takeaway"] == "Video 1"


@pytest.mark.asyncio
async def test_fetch_stage_execute_uses_default_output_when_stage_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(stage_mod, "get_json", lambda cache, key: None)
    monkeypatch.setattr(stage_mod, "set_json", lambda cache, key, value: None)

    ctx = _ctx(tmp_path, cfg=_Cfg(stages={"fetch": False}))
    output = await stage_mod.FetchStage().execute(ctx)

    assert output == {"items": [], "signals": []}
    assert ctx.outputs["fetch"] == output


@pytest.mark.asyncio
async def test_score_stage_execute_uses_cached_output_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(stage_mod, "stage_cache", lambda name: name)
    monkeypatch.setattr(
        stage_mod,
        "get_json",
        lambda cache, key: {
            "output": {"all_scored": [{"title": "cached"}], "top_n": [{"title": "cached"}]}
        },
    )
    monkeypatch.setattr(
        stage_mod,
        "set_json",
        lambda cache, key, value: (_ for _ in ()).throw(AssertionError("cache write not expected")),
    )

    ctx = _ctx(tmp_path, outputs={"fetch": {"items": [], "signals": []}})
    output = await stage_mod.ScoreStage().execute(ctx)

    assert output["top_n"][0]["title"] == "cached"
    assert ctx.outputs["score"] == output


@pytest.mark.asyncio
async def test_fetch_stage_run_and_cache_payload_roundtrip(tmp_path):
    ctx = _ctx(tmp_path)
    stage = stage_mod.FetchStage()

    output = await stage.run(ctx)
    payload = stage.to_cache_payload(output)
    restored = stage.from_cache_payload(payload)

    assert output["items"][0].title == "Video 1"
    assert restored["items"][0].title == "Video 1"
    assert restored["signals"][0].upload_date == _NOW


@pytest.mark.asyncio
async def test_fetch_stage_run_returns_default_when_service_or_technology_off(tmp_path):
    stage = stage_mod.FetchStage()
    service_ctx = _ctx(tmp_path, cfg=_Cfg(services={"platform_api": False}))
    tech_ctx = _ctx(tmp_path, cfg=_Cfg(technologies={"youtube_api": False}))

    assert await stage.run(service_ctx) == {"items": [], "signals": []}
    assert await stage.run(tech_ctx) == {"items": [], "signals": []}


@pytest.mark.asyncio
async def test_score_stage_fallback_and_default_output(tmp_path):
    fetch_output = {"items": [_raw_item()], "signals": [_signal()]}
    ctx = _ctx(tmp_path, cfg=_Cfg(services={"scoring": False}), outputs={"fetch": fetch_output})
    stage = stage_mod.ScoreStage()

    fallback = await stage.run(ctx)
    defaulted = stage.default_output(ctx)

    assert fallback["top_n"]
    assert defaulted["top_n"]
    assert stage.cache_key(ctx)


@pytest.mark.asyncio
async def test_enrich_stage_branches(tmp_path, monkeypatch):
    stage = stage_mod.EnrichStage()
    top_n = [{"title": "Video 1"}]

    non_youtube_ctx = _ctx(tmp_path, platform="tiktok", outputs={"score": {"top_n": top_n}})
    assert await stage.run(non_youtube_ctx) == {"top_n": top_n}

    no_service_ctx = _ctx(
        tmp_path,
        cfg=_Cfg(
            services={
                "transcripts": False,
                "llm": False,
                "media_url_summary": False,
                "merged_summary": False,
            }
        ),
        outputs={"score": {"top_n": top_n}},
    )
    assert await stage.run(no_service_ctx) == {"top_n": top_n}
    assert stage.default_output(no_service_ctx) == {"top_n": top_n}

    called = []

    async def _fake_enrich(items, *, cfg=None):
        called.append((items, cfg))

    monkeypatch.setattr(stage_mod._enrich_mod, "_enrich_top_n_with_transcripts", _fake_enrich)
    active_ctx = _ctx(tmp_path, outputs={"score": {"top_n": top_n}})
    assert await stage.run(active_ctx) == {"top_n": top_n}
    assert called
    assert stage.cache_key(active_ctx)


@pytest.mark.asyncio
async def test_corroborate_and_analyze_default_paths(tmp_path):
    stage = stage_mod.CorroborateStage()
    top_n = [{"title": "Video 1"}]
    disabled_ctx = _ctx(
        tmp_path,
        cfg=_Cfg(services={"corroboration": False}),
        outputs={"enrich": {"top_n": top_n}},
    )

    assert await stage.run(disabled_ctx) == {"top_n": top_n, "backends": [], "results": []}
    assert stage.default_output(disabled_ctx) == {"top_n": top_n, "backends": [], "results": []}

    analyze_default = stage_mod.AnalyzeStage().default_output(_ctx(tmp_path))
    assert analyze_default["warnings"] == []
    assert analyze_default["source_validation_summary"]["unverified"] == 0
