"""Explicit research pipeline stages with per-stage cacheable outputs."""

from __future__ import annotations

import asyncio
import copy
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from social_research_probe.config import Config
from social_research_probe.platforms.base import (
    FetchLimits,
    PlatformAdapter,
    RawItem,
    SignalSet,
)
from social_research_probe.scoring.combine import DEFAULT_WEIGHTS
from social_research_probe.synthesize.warnings import detect as detect_warnings
from social_research_probe.types import AdapterConfig, ScoredItem
from social_research_probe.utils.pipeline_cache import get_json, hash_key, set_json, stage_cache
from social_research_probe.utils.service_log import service_log
from social_research_probe.validation.source import classify as classify_source

from . import corroboration as _corr_mod
from . import enrichment as _enrich_mod
from .charts import _chart_takeaways, _render_charts
from .scoring import _score_item, _zscore
from .stats import _build_stats_summary
from .svs import _build_svs


def _json_key(name: str, payload: dict[str, object]) -> str:
    return hash_key(name, json.dumps(payload, sort_keys=True, default=str))


def _platform_api_technology(platform: str) -> str:
    return f"{platform}_api"


def _stage_enabled(cfg: object, name: str, *, default: bool = True) -> bool:
    fn = getattr(cfg, "stage_enabled", None)
    if callable(fn):
        return bool(fn(name))
    return default


def _service_enabled(cfg: object, name: str, *, default: bool = True) -> bool:
    fn = getattr(cfg, "service_enabled", None)
    if callable(fn):
        return bool(fn(name))
    return default


def _technology_enabled(cfg: object, name: str, *, default: bool = True) -> bool:
    fn = getattr(cfg, "technology_enabled", None)
    if callable(fn):
        return bool(fn(name))
    return default


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _dt_from_str(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _raw_item_to_dict(item: RawItem) -> dict[str, object]:
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "author_id": item.author_id,
        "author_name": item.author_name,
        "published_at": _dt_to_str(item.published_at),
        "metrics": item.metrics,
        "text_excerpt": item.text_excerpt,
        "thumbnail": item.thumbnail,
        "extras": item.extras,
    }


def _raw_item_from_dict(data: dict[str, object]) -> RawItem:
    return RawItem(
        id=str(data.get("id", "")),
        url=str(data.get("url", "")),
        title=str(data.get("title", "")),
        author_id=str(data.get("author_id", "")),
        author_name=str(data.get("author_name", "")),
        published_at=_dt_from_str(data.get("published_at")) or datetime.now().astimezone(),
        metrics=data.get("metrics", {}),
        text_excerpt=data.get("text_excerpt"),
        thumbnail=data.get("thumbnail"),
        extras=data.get("extras", {}),
    )


def _signal_to_dict(signal: SignalSet) -> dict[str, object]:
    return {
        "views": signal.views,
        "likes": signal.likes,
        "comments": signal.comments,
        "upload_date": _dt_to_str(signal.upload_date),
        "view_velocity": signal.view_velocity,
        "engagement_ratio": signal.engagement_ratio,
        "comment_velocity": signal.comment_velocity,
        "cross_channel_repetition": signal.cross_channel_repetition,
        "raw": signal.raw,
    }


def _signal_from_dict(data: dict[str, object]) -> SignalSet:
    return SignalSet(
        views=data.get("views"),
        likes=data.get("likes"),
        comments=data.get("comments"),
        upload_date=_dt_from_str(data.get("upload_date")),
        view_velocity=data.get("view_velocity"),
        engagement_ratio=data.get("engagement_ratio"),
        comment_velocity=data.get("comment_velocity"),
        cross_channel_repetition=data.get("cross_channel_repetition"),
        raw=data.get("raw", {}),
    )


def _fallback_scored_items(
    items: list[RawItem],
    signals: list[SignalSet],
    adapter: PlatformAdapter,
    *,
    top_n: int,
) -> dict[str, list[ScoredItem]]:
    scored: list[ScoredItem] = []
    for item, signal in zip(items, signals, strict=True):
        hints = adapter.trust_hints(item)
        src = classify_source(item, hints)
        scored.append(
            {
                "title": item.title,
                "channel": item.author_name,
                "url": item.url,
                "source_class": src.value,
                "scores": {
                    "trust": 0.0,
                    "trend": 0.0,
                    "opportunity": 0.0,
                    "overall": 0.0,
                },
                "features": {
                    "view_velocity": float(signal.view_velocity or 0.0),
                    "engagement_ratio": float(signal.engagement_ratio or 0.0),
                    "age_days": float(
                        max(
                            1.0,
                            (
                                (datetime.now(item.published_at.tzinfo) - item.published_at).days
                                if item.published_at
                                else 30.0
                            ),
                        )
                    ),
                    "subscriber_count": float(hints.subscriber_count or 0.0),
                },
                "one_line_takeaway": (item.text_excerpt or item.title)[:140],
            }
        )
    return {"all_scored": scored, "top_n": copy.deepcopy(scored[:top_n])}


@dataclass
class StageExecutionContext:
    cfg: Config
    cmd: object
    data_dir: object
    adapter: PlatformAdapter
    platform_config: AdapterConfig
    limits: FetchLimits
    topic: str
    purpose_names: list[str]
    search_topic: str
    scoring_weights: dict[str, float]
    timings: dict[str, list]
    outputs: dict[str, dict[str, object]]
    corroboration_backends: list[str] | None = None

    def output(self, name: str) -> dict[str, object]:
        return self.outputs.get(name, {})

    def top_n_limit(self) -> int:
        return int(self.platform_config.get("enrich_top_n", 5))

    def platform_technology(self) -> str:
        return _platform_api_technology(self.cmd.platform)


class ResearchStage(ABC):
    name: str

    async def execute(self, ctx: StageExecutionContext) -> dict[str, object]:
        if not _stage_enabled(ctx.cfg, self.name):
            output = self.default_output(ctx)
            ctx.outputs[self.name] = output
            return output

        key = self.cache_key(ctx)
        cache = stage_cache(self.name)
        cached = get_json(cache, key)
        if cached and isinstance(cached.get("output"), dict):
            output = self.from_cache_payload(cached["output"])
            ctx.outputs[self.name] = output
            return output

        async with service_log(self.name, packet=ctx.timings, cfg_logs_enabled=False):
            output = await self.run(ctx)
        set_json(cache, key, {"output": self.to_cache_payload(output)})
        ctx.outputs[self.name] = output
        return output

    @abstractmethod
    async def run(self, ctx: StageExecutionContext) -> dict[str, object]: ...

    @abstractmethod
    def default_output(self, ctx: StageExecutionContext) -> dict[str, object]: ...

    @abstractmethod
    def cache_key(self, ctx: StageExecutionContext) -> str: ...

    def to_cache_payload(self, output: dict[str, object]) -> dict[str, object]:
        return output

    def from_cache_payload(self, payload: dict[str, object]) -> dict[str, object]:
        return payload


class FetchStage(ResearchStage):
    name = "fetch"

    async def run(self, ctx: StageExecutionContext) -> dict[str, object]:
        if not (
            _stage_enabled(ctx.cfg, self.name)
            and _service_enabled(ctx.cfg, "platform_api")
            and _technology_enabled(ctx.cfg, ctx.platform_technology())
        ):
            return self.default_output(ctx)

        raw_items = await asyncio.to_thread(
            lambda: ctx.adapter.search(ctx.search_topic, ctx.limits)
        )
        items = await ctx.adapter.enrich(raw_items)
        signals = ctx.adapter.to_signals(items)
        return {"items": items, "signals": signals}

    def default_output(self, _ctx: StageExecutionContext) -> dict[str, object]:
        return {"items": [], "signals": []}

    def cache_key(self, ctx: StageExecutionContext) -> str:
        return _json_key(
            self.name,
            {
                "platform": ctx.cmd.platform,
                "topic": ctx.search_topic,
                "max_items": ctx.limits.max_items,
                "recency_days": ctx.limits.recency_days,
                "platform_api": _service_enabled(ctx.cfg, "platform_api"),
                "technology": _technology_enabled(ctx.cfg, ctx.platform_technology()),
            },
        )

    def to_cache_payload(self, output: dict[str, object]) -> dict[str, object]:
        return {
            "items": [_raw_item_to_dict(item) for item in output.get("items", [])],
            "signals": [_signal_to_dict(signal) for signal in output.get("signals", [])],
        }

    def from_cache_payload(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "items": [_raw_item_from_dict(item) for item in payload.get("items", [])],
            "signals": [_signal_from_dict(signal) for signal in payload.get("signals", [])],
        }


class ScoreStage(ResearchStage):
    name = "score"

    async def run(self, ctx: StageExecutionContext) -> dict[str, object]:
        fetch = ctx.output("fetch")
        items = fetch.get("items", [])
        signals = fetch.get("signals", [])
        if not (_stage_enabled(ctx.cfg, self.name) and _service_enabled(ctx.cfg, "scoring")):
            return _fallback_scored_items(
                items,
                signals,
                ctx.adapter,
                top_n=ctx.top_n_limit(),
            )

        hints = [ctx.adapter.trust_hints(item) for item in items]
        z_vels = _zscore([signal.view_velocity or 0.0 for signal in signals])
        z_engs = _zscore([signal.engagement_ratio or 0.0 for signal in signals])
        scored = [
            _score_item(item, signal, hint, z_vel, z_eng, ctx.scoring_weights or DEFAULT_WEIGHTS)
            for item, signal, hint, z_vel, z_eng in zip(
                items, signals, hints, z_vels, z_engs, strict=True
            )
        ]
        scored.sort(key=lambda row: row[0], reverse=True)
        all_scored = [item for _, item in scored]
        return {"all_scored": all_scored, "top_n": copy.deepcopy(all_scored[: ctx.top_n_limit()])}

    def default_output(self, ctx: StageExecutionContext) -> dict[str, object]:
        fetch = ctx.output("fetch")
        return _fallback_scored_items(
            fetch.get("items", []),
            fetch.get("signals", []),
            ctx.adapter,
            top_n=ctx.top_n_limit(),
        )

    def cache_key(self, ctx: StageExecutionContext) -> str:
        fetch = self.to_cache_payload(ctx.output("fetch"))
        return _json_key(
            self.name,
            {
                "fetch": fetch,
                "weights": ctx.scoring_weights,
                "top_n": ctx.top_n_limit(),
                "scoring": _service_enabled(ctx.cfg, "scoring"),
            },
        )


class EnrichStage(ResearchStage):
    name = "enrich"

    async def run(self, ctx: StageExecutionContext) -> dict[str, object]:
        top_n = copy.deepcopy(ctx.output("score").get("top_n", []))
        if ctx.cmd.platform != "youtube":
            return {"top_n": top_n}
        if not ctx.platform_config.get("fetch_transcripts", True):
            return {"top_n": top_n}
        if not any(
            (
                _service_enabled(ctx.cfg, "transcripts"),
                _service_enabled(ctx.cfg, "llm"),
                _service_enabled(ctx.cfg, "media_url_summary"),
                _service_enabled(ctx.cfg, "merged_summary"),
            )
        ):
            return {"top_n": top_n}
        await _enrich_mod._enrich_top_n_with_transcripts(top_n, cfg=ctx.cfg)
        return {"top_n": top_n}

    def default_output(self, ctx: StageExecutionContext) -> dict[str, object]:
        return {"top_n": copy.deepcopy(ctx.output("score").get("top_n", []))}

    def cache_key(self, ctx: StageExecutionContext) -> str:
        return _json_key(
            self.name,
            {
                "platform": ctx.cmd.platform,
                "top_n": ctx.output("score").get("top_n", []),
                "transcripts": _service_enabled(ctx.cfg, "transcripts"),
                "llm": _service_enabled(ctx.cfg, "llm"),
                "media_url_summary": _service_enabled(ctx.cfg, "media_url_summary"),
                "merged_summary": _service_enabled(ctx.cfg, "merged_summary"),
                "youtube_transcript_api": _technology_enabled(ctx.cfg, "youtube_transcript_api"),
                "whisper": _technology_enabled(ctx.cfg, "whisper"),
                "gemini": _technology_enabled(ctx.cfg, "gemini"),
                "claude": _technology_enabled(ctx.cfg, "claude"),
                "codex": _technology_enabled(ctx.cfg, "codex"),
                "local": _technology_enabled(ctx.cfg, "local"),
            },
        )


class CorroborateStage(ResearchStage):
    name = "corroborate"

    async def run(self, ctx: StageExecutionContext) -> dict[str, object]:
        top_n = copy.deepcopy(ctx.output("enrich").get("top_n", []))
        if not (_stage_enabled(ctx.cfg, self.name) and _service_enabled(ctx.cfg, "corroboration")):
            return {"top_n": top_n, "backends": [], "results": []}
        backends = list(ctx.corroboration_backends or [])
        results = await _corr_mod._corroborate_top_n(top_n, backends) if backends else []
        for item, result in zip(top_n, results, strict=False):
            verdict = result.get("aggregate_verdict")
            if isinstance(verdict, str):
                item["corroboration_verdict"] = verdict
        return {"top_n": top_n, "backends": backends, "results": results}

    def default_output(self, ctx: StageExecutionContext) -> dict[str, object]:
        return {
            "top_n": copy.deepcopy(ctx.output("enrich").get("top_n", [])),
            "backends": [],
            "results": [],
        }

    def cache_key(self, ctx: StageExecutionContext) -> str:
        return _json_key(
            self.name,
            {
                "top_n": ctx.output("enrich").get("top_n", []),
                "configured_backend": ctx.cfg.corroboration_backend,
                "backends": ctx.corroboration_backends or [],
                "corroboration": _service_enabled(ctx.cfg, "corroboration"),
                "llm": _service_enabled(ctx.cfg, "llm"),
                "llm_search": _technology_enabled(ctx.cfg, "llm_search"),
                "exa": _technology_enabled(ctx.cfg, "exa"),
                "brave": _technology_enabled(ctx.cfg, "brave"),
                "tavily": _technology_enabled(ctx.cfg, "tavily"),
                "runner": ctx.cfg.llm_runner,
            },
        )


class AnalyzeStage(ResearchStage):
    name = "analyze"

    async def run(self, ctx: StageExecutionContext) -> dict[str, object]:
        fetch = ctx.output("fetch")
        scored = ctx.output("score")
        corroborate = ctx.output("corroborate")
        all_scored = scored.get("all_scored", [])
        top_n = corroborate.get("top_n", [])
        results = corroborate.get("results", [])
        backends = corroborate.get("backends", [])

        stats_summary = (
            _build_stats_summary(all_scored)
            if _service_enabled(ctx.cfg, "statistics")
            else {"models_run": [], "highlights": [], "low_confidence": True}
        )
        chart_captions = (
            _render_charts(all_scored, ctx.data_dir) if _service_enabled(ctx.cfg, "charts") else []
        )
        chart_takeaways = (
            _chart_takeaways(all_scored) if _service_enabled(ctx.cfg, "chart_takeaways") else []
        )
        svs = _build_svs(top_n, results, backends)
        cfg_corr = ctx.cfg.corroboration_backend
        skip_reason: str | None = None
        if not backends:
            skip_reason = (
                "disabled in config"
                if cfg_corr == "none"
                else "no API credentials usable — run 'srp config check-secrets'"
            )
        warnings = detect_warnings(
            fetch.get("items", []),
            fetch.get("signals", []),
            top_n,
            corroboration_ran=bool(backends and top_n),
            corroboration_skip_reason=skip_reason,
        )
        return {
            "source_validation_summary": svs,
            "stats_summary": stats_summary,
            "chart_captions": chart_captions,
            "chart_takeaways": chart_takeaways,
            "warnings": warnings,
        }

    def default_output(self, _ctx: StageExecutionContext) -> dict[str, object]:
        return {
            "source_validation_summary": {
                "validated": 0,
                "partially": 0,
                "unverified": 0,
                "low_trust": 0,
                "primary": 0,
                "secondary": 0,
                "commentary": 0,
                "notes": "analysis stage disabled",
            },
            "stats_summary": {"models_run": [], "highlights": [], "low_confidence": True},
            "chart_captions": [],
            "chart_takeaways": [],
            "warnings": [],
        }

    def cache_key(self, ctx: StageExecutionContext) -> str:
        return _json_key(
            self.name,
            {
                "all_scored": ctx.output("score").get("all_scored", []),
                "top_n": ctx.output("corroborate").get("top_n", []),
                "results": ctx.output("corroborate").get("results", []),
                "backends": ctx.output("corroborate").get("backends", []),
                "statistics": _service_enabled(ctx.cfg, "statistics"),
                "charts": _service_enabled(ctx.cfg, "charts"),
                "chart_takeaways": _service_enabled(ctx.cfg, "chart_takeaways"),
            },
        )


RESEARCH_STAGES: tuple[ResearchStage, ...] = (
    FetchStage(),
    ScoreStage(),
    EnrichStage(),
    CorroborateStage(),
    AnalyzeStage(),
)


async def execute_research_stages(ctx: StageExecutionContext) -> dict[str, dict[str, object]]:
    """Run the configured research stages in declared order."""
    for stage in RESEARCH_STAGES:
        await stage.execute(ctx)
    return ctx.outputs
