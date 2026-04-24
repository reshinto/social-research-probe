"""Top-level research orchestrator: adapter setup, topic loop, packet assembly."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from social_research_probe.commands.parse import ParsedRunResearch
from social_research_probe.config import Config
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.platform import YouTubePipeline, run_all_platforms
from social_research_probe.platform.state import PipelineState
from social_research_probe.platforms.base import FetchLimits
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.purposes import registry as purpose_registry
from social_research_probe.purposes.merge import MergedPurpose, merge_purposes
from social_research_probe.scoring.combine import DEFAULT_WEIGHTS
from social_research_probe.utils.core.types import AdapterConfig, MultiResearchPacket, ResearchPacket
from social_research_probe.utils.fast_mode import (
    FAST_MODE_MAX_BACKENDS,
    FAST_MODE_TOP_N,
    fast_mode_enabled,
)
from social_research_probe.utils.progress import log

from .scoring import _enrich_query


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


def _auto_mode_backends(cfg: Config) -> tuple[str, ...]:
    """Return the ordered tuple of backend names to try in auto mode.

    Each backend has its own technology gate; a disabled backend is removed
    from the candidate list without affecting the others.
    """
    return tuple(
        name for name in ("exa", "brave", "tavily", "llm_search") if _technology_enabled(cfg, name)
    )


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


def _available_backends(data_dir: Path, cfg=None) -> list[str]:
    """Return corroboration backends allowed by config and available at runtime.

    ``backend = auto`` auto-discovers the configured search backends whose
    credentials or runner capabilities are usable. A specific backend value
    uses only that backend. ``backend = none`` disables corroboration entirely.
    """
    from social_research_probe.corroboration.registry import get_backend

    if cfg is None:
        cfg = Config.load(data_dir)
    configured = cfg.corroboration_backend
    if not _stage_enabled(cfg, "corroborate"):
        log("[srp] corroboration: disabled by stages.corroborate = false.")
        return []
    if not _service_enabled(cfg, "corroboration"):
        log("[srp] corroboration: disabled by services.corroboration = false.")
        return []
    if configured == "none":
        log(
            "[srp] corroboration: disabled in config (corroboration.backend = 'none'). Enable with 'srp config set corroboration.backend auto'."
        )
        return []
    auto_candidates = _auto_mode_backends(cfg)
    candidates = auto_candidates if configured == "auto" else (configured,)

    available: list[str] = []
    for name in candidates:
        if not _technology_enabled(cfg, name):
            continue
        if name == "llm_search" and not _service_enabled(cfg, "llm"):
            continue
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
    fetch_technology = f"{cmd.platform}_api"
    if (
        _stage_enabled(cfg, "fetch")
        and _service_enabled(cfg, "platform_api")
        and _technology_enabled(cfg, fetch_technology)
        and not await asyncio.to_thread(adapter.health_check)
    ):
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
        backends = _available_backends(data_dir, cfg=cfg)
        if fast_mode_enabled():
            backends = backends[:FAST_MODE_MAX_BACKENDS]
        if fast_mode_enabled():
            platform_config["enrich_top_n"] = min(
                int(platform_config.get("enrich_top_n", 5)),
                FAST_MODE_TOP_N,
            )
        state = PipelineState(
            platform_type=cmd.platform if cmd.platform != "all" else "youtube",
            cfg=cfg,
            cmd=cmd,
            data_dir=data_dir,
            cache=None,
            inputs={
                "adapter": adapter,
                "platform_config": platform_config,
                "limits": limits,
                "topic": topic,
                "purpose_names": list(merged.names),
                "search_topic": search_topic,
                "scoring_weights": scoring_weights,
                "timings": timings,
                "corroboration_backends": backends,
            },
        )
        if cmd.platform == "all":
            state = await run_all_platforms(state)
        else:
            state = await YouTubePipeline().run(state)
        packet = state.outputs.get("packet", {})
        packet["stage_timings"] = list(timings.get("stage_timings", []))
        packets.append(packet)

    combined = packets[0] if len(packets) == 1 else {"multi": packets}
    return combined
