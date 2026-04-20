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
from social_research_probe.purposes.merge import merge_purposes
from social_research_probe.synthesize.evidence import summarize as summarize_evidence
from social_research_probe.synthesize.evidence import summarize_signals
from social_research_probe.synthesize.formatter import build_packet
from social_research_probe.synthesize.warnings import detect as detect_warnings
from social_research_probe.types import AdapterConfig, MultiResearchPacket, ResearchPacket
from social_research_probe.utils.progress import log

from . import corroboration as _corr_mod
from . import enrichment as _enrich_mod
from .charts import _render_charts
from .scoring import _enrich_query, _score_item, _zscore
from .stats import _build_stats_summary
from .svs import _build_svs


def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        importlib.import_module("tests.fixtures.fake_youtube")


def _available_backends(data_dir: Path) -> list[str]:
    """Return corroboration backends allowed by config and available at runtime.

    ``backend = host`` auto-discovers the web-search backends whose credentials
    are configured. ``backend = llm_cli`` or a specific search backend uses only
    that backend. ``backend = none`` disables corroboration entirely.
    """
    from social_research_probe.corroboration.registry import get_backend

    configured = Config.load(data_dir).corroboration_backend
    if configured == "none":
        log(
            "[srp] corroboration: disabled in config (corroboration.backend = 'none'). Enable with 'srp config set corroboration.backend host'."
        )
        return []
    candidates = ("exa", "brave", "tavily") if configured == "host" else (configured,)

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
        search_topic = _enrich_query(topic, merged.method)
        raw_items = await asyncio.to_thread(
            lambda st=search_topic, lm=limits: adapter.search(st, lm)
        )
        items = await adapter.enrich(raw_items)
        signals = adapter.to_signals(items)
        hints = [adapter.trust_hints(it) for it in items]
        z_vels = _zscore([s.view_velocity or 0.0 for s in signals])
        z_engs = _zscore([s.engagement_ratio or 0.0 for s in signals])
        scored = [
            _score_item(item, signal, hint, z_vel, z_eng)
            for item, signal, hint, z_vel, z_eng in zip(
                items, signals, hints, z_vels, z_engs, strict=True
            )
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        all_scored = [d for _, d in scored]
        enrich_top_n = int(platform_config.get("enrich_top_n", 5))
        top5 = all_scored[:enrich_top_n]
        if platform_config.get("fetch_transcripts", True) and cmd.platform == "youtube":
            await _enrich_mod._enrich_top5_with_transcripts(top5)
        backends = _available_backends(data_dir)
        corroboration_results = (
            await _corr_mod._corroborate_top5(top5, backends) if backends else []
        )
        svs = _build_svs(top5, corroboration_results, backends)
        stats_summary = _build_stats_summary(all_scored)
        chart_captions = _render_charts(all_scored, data_dir)
        cfg_corr = Config.load(data_dir).corroboration_backend
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
        packets.append(
            build_packet(
                topic=topic,
                platform=cmd.platform,
                purpose_set=list(merged.names),
                items_top5=top5,
                source_validation_summary=svs,
                platform_signals_summary=summarize_signals(signals),
                evidence_summary=summarize_evidence(items, signals, top5),
                stats_summary=stats_summary,
                chart_captions=chart_captions,
                warnings=warnings,
            )
        )

    combined = packets[0] if len(packets) == 1 else {"multi": packets}
    return combined
