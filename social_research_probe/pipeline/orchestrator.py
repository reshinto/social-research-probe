"""Top-level research orchestrator: adapter setup, topic loop, packet assembly."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.config import Config
from social_research_probe.errors import ValidationError
from social_research_probe.platforms.base import FetchLimits
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.purposes import registry as purpose_registry
from social_research_probe.purposes.merge import MergedPurpose, merge_purposes
from social_research_probe.scoring.combine import DEFAULT_WEIGHTS
from social_research_probe.synthesize.evidence import summarize as summarize_evidence
from social_research_probe.synthesize.evidence import summarize_signals
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.synthesize.warnings import detect as detect_warnings
from social_research_probe.types import AdapterConfig, MultiResearchPacket, ResearchPacket
from social_research_probe.utils.fast_mode import (
    FAST_MODE_MAX_BACKENDS,
    FAST_MODE_TOP_N,
    fast_mode_enabled,
)
from social_research_probe.utils.progress import log
from social_research_probe.utils.service_log import service_log

from . import corroboration as _corr_mod
from . import enrichment as _enrich_mod
from .charts import _chart_takeaways, _render_charts
from .scoring import _enrich_query, _score_item, _zscore
from .stats import _build_stats_summary
from .svs import _build_svs


def _resolve_scoring_weights(cfg: Config, merged: MergedPurpose) -> dict[str, float]:
    """Merge spec §6 defaults with config-wide overrides, then purpose-specific overrides.

    Precedence (later wins): DEFAULT_WEIGHTS → [scoring.weights] in config.toml →
    merged purpose ``scoring_overrides``. Only keys ``trust``, ``trend``, and
    ``opportunity`` are recognised; unknown keys are silently ignored.
    """
    resolved: dict[str, float] = dict(DEFAULT_WEIGHTS)
    config_weights = cfg.raw.get("scoring", {}).get("weights", {})
    for key in ("trust", "trend", "opportunity"):
        if key in config_weights:
            resolved[key] = float(config_weights[key])
        if key in merged.scoring_overrides:
            resolved[key] = float(merged.scoring_overrides[key])
    return resolved


def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        importlib.import_module("tests.fixtures.fake_youtube")


def _divergence_warnings(top5: list, cfg: Config) -> list[str]:
    """Return warning strings for top-5 items whose summary divergence exceeds threshold."""
    threshold = float(getattr(cfg, "tunables", {}).get("summary_divergence_threshold", 0.4))
    out: list[str] = []
    for item in top5:
        divergence = item.get("summary_divergence")
        if divergence is None:
            continue
        if divergence > threshold:
            title = (item.get("title") or "untitled")[:80]
            out.append(f"summary/transcript divergence on {title!r}: {divergence:.2f}")
    return out


def _host_mode_backends(cfg: Config, feature_enabled=None) -> tuple[str, ...]:
    """Return the ordered tuple of backend names to try in host-auto mode.

    Each backend has its own feature flag; a flag set to False removes that
    backend from the candidate list without affecting the others. ``feature_enabled``
    may be passed in (e.g. when ``cfg`` is a test stub without the method);
    defaults to ``cfg.feature_enabled``.
    """
    fn = feature_enabled or getattr(cfg, "feature_enabled", lambda _name: True)
    flag_by_backend = (
        ("exa", "exa_enabled"),
        ("brave", "brave_enabled"),
        ("tavily", "tavily_enabled"),
        ("gemini_search", "gemini_search_enabled"),
    )
    return tuple(name for name, flag in flag_by_backend if fn(flag))


def _available_backends(data_dir: Path, cfg=None) -> list[str]:
    """Return corroboration backends allowed by config and available at runtime.

    ``backend = host`` auto-discovers the web-search backends whose credentials
    are configured. ``backend = llm_cli`` or a specific search backend uses only
    that backend. ``backend = none`` disables corroboration entirely.
    """
    from social_research_probe.corroboration.registry import get_backend

    if cfg is None:
        cfg = Config.load(data_dir)
    configured = cfg.corroboration_backend
    feature_enabled = getattr(cfg, "feature_enabled", lambda _name: True)
    if configured == "none" or not feature_enabled("corroboration_enabled"):
        log(
            "[srp] corroboration: disabled in config (corroboration.backend = 'none'). Enable with 'srp config set corroboration.backend host'."
        )
        return []
    host_candidates = _host_mode_backends(cfg, feature_enabled)
    candidates = host_candidates if configured == "host" else (configured,)

    available: list[str] = []
    for name in candidates:
        try:
            if get_backend(name).health_check():
                available.append(name)
        except ValidationError:
            pass

    if not available:
        checked = ", ".join(candidates)
        log(
            f"[srp] corroboration: backend '{configured}' configured but no provider usable"
            f" (checked: {checked}). Hint: run 'srp config check-secrets --corroboration {configured}'."
        )
    return available


async def run_research(
    cmd: ParsedRunResearch,
    data_dir: Path,
    adapter_config: AdapterConfig | None = None,
) -> ResearchPacket | MultiResearchPacket:
    _maybe_register_fake()
    os.environ["SRP_DATA_DIR"] = str(data_dir)
    purposes = purpose_registry.load(data_dir)["purposes"]
    cfg = Config.load(data_dir)
    feature_enabled = getattr(cfg, "feature_enabled", lambda _name: True)
    platform_config: AdapterConfig = {
        **cfg.platform_defaults(cmd.platform),
        "data_dir": data_dir,
        **(adapter_config or {}),
    }
    limits = FetchLimits(
        max_items=int(platform_config.get("max_items", FetchLimits.max_items)),
        recency_days=platform_config.get("recency_days", FetchLimits.recency_days),
    )
    adapter = get_adapter(cmd.platform, platform_config)
    if not await asyncio.to_thread(adapter.health_check):
        raise ValidationError(f"adapter {cmd.platform} failed health check")

    packets: list[ResearchPacket] = []
    for topic, purpose_names in cmd.topics:
        for n in purpose_names:
            if n not in purposes:
                raise ValidationError(f"unknown purpose: {n!r}")
        merged = merge_purposes(purposes, list(purpose_names))
        scoring_weights = _resolve_scoring_weights(cfg, merged)
        search_topic = _enrich_query(topic, merged.method)
        timings: dict = {"stage_timings": []}
        cfg_logs = bool(getattr(cfg, "logging", {}).get("service_logs_enabled", False))
        async with service_log("fetch", packet=timings, cfg_logs_enabled=cfg_logs):
            raw_items = await asyncio.to_thread(
                lambda st=search_topic, lm=limits: adapter.search(st, lm)
            )
            items = await adapter.enrich(raw_items)
            signals = adapter.to_signals(items)
        async with service_log("score", packet=timings, cfg_logs_enabled=cfg_logs):
            hints = [adapter.trust_hints(it) for it in items]
            z_vels = _zscore([s.view_velocity or 0.0 for s in signals])
            z_engs = _zscore([s.engagement_ratio or 0.0 for s in signals])
            scored = [
                _score_item(item, signal, hint, z_vel, z_eng, scoring_weights)
                for item, signal, hint, z_vel, z_eng in zip(
                    items, signals, hints, z_vels, z_engs, strict=True
                )
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            all_scored = [d for _, d in scored]
        enrich_top_n = int(platform_config.get("enrich_top_n", 5))
        if fast_mode_enabled():
            enrich_top_n = min(enrich_top_n, FAST_MODE_TOP_N)
        top5 = all_scored[:enrich_top_n]
        if (
            platform_config.get("fetch_transcripts", True)
            and cmd.platform == "youtube"
            and feature_enabled("enrichment_enabled")
        ):
            async with service_log("enrich", packet=timings, cfg_logs_enabled=cfg_logs):
                await _enrich_mod._enrich_top5_with_transcripts(top5)
        backends = _available_backends(data_dir, cfg=cfg)
        if fast_mode_enabled():
            backends = backends[:FAST_MODE_MAX_BACKENDS]
        async with service_log("corroborate", packet=timings, cfg_logs_enabled=cfg_logs):
            corroboration_results = (
                await _corr_mod._corroborate_top5(top5, backends) if backends else []
            )
        for item, result in zip(top5, corroboration_results, strict=False):
            verdict = result.get("aggregate_verdict")
            if isinstance(verdict, str):
                item["corroboration_verdict"] = verdict
        svs = _build_svs(top5, corroboration_results, backends)
        stats_summary = _build_stats_summary(all_scored)
        async with service_log("charts", packet=timings, cfg_logs_enabled=cfg_logs):
            chart_captions = (
                _render_charts(all_scored, data_dir) if feature_enabled("charts_enabled") else []
            )
            chart_takeaways = (
                _chart_takeaways(all_scored) if feature_enabled("chart_takeaways_enabled") else []
            )
        cfg_corr = cfg.corroboration_backend
        skip_reason: str | None = None
        if not backends:
            skip_reason = (
                "disabled in config"
                if cfg_corr == "none"
                else "no API credentials usable — run 'srp config check-secrets'"
            )
        warnings = detect_warnings(
            items,
            signals,
            top5,
            corroboration_ran=bool(backends and top5),
            corroboration_skip_reason=skip_reason,
        )
        warnings.extend(_divergence_warnings(top5, cfg))
        async with service_log("synthesize", packet=timings, cfg_logs_enabled=cfg_logs):
            packet = build_packet(
                topic=topic,
                platform=cmd.platform,
                purpose_set=list(merged.names),
                items_top5=top5,
                source_validation_summary=svs,
                platform_signals_summary=summarize_signals(signals),
                evidence_summary=summarize_evidence(items, signals, top5),
                stats_summary=stats_summary,
                chart_captions=chart_captions,
                chart_takeaways=chart_takeaways,
                warnings=warnings,
            )
        packet["stage_timings"] = list(timings["stage_timings"])
        packets.append(packet)

    combined = packets[0] if len(packets) == 1 else {"multi": packets}
    return combined
