"""Top-level research orchestrator: adapter setup, topic loop, packet assembly."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from social_research_probe.cli.dsl_parser import ParsedRunResearch
from social_research_probe.config import Config
from social_research_probe.platforms.base import FetchLimits
from social_research_probe.platforms.platform import YouTubePipeline, run_all_platforms
from social_research_probe.platforms.platform.state import PipelineState
from social_research_probe.platforms.registry import get_adapter
from social_research_probe.services.corroborating.backends import (
    auto_mode_backends,
    available_backends,
)
from social_research_probe.services.scoring.weights import resolve_scoring_weights
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import (
    AdapterConfig,
    MultiResearchPacket,
    ResearchPacket,
)
from social_research_probe.utils.display.fast_mode import (
    FAST_MODE_MAX_BACKENDS,
    FAST_MODE_TOP_N,
    fast_mode_enabled,
)
from social_research_probe.utils.display.progress import log
from social_research_probe.utils.purposes import registry as purpose_registry
from social_research_probe.utils.purposes.merge import MergedPurpose, merge_purposes
from social_research_probe.utils.search.query import enrich_query



def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        importlib.import_module("tests.fixtures.fake_youtube")


async def run_pipeline(
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
        cfg.stage_enabled("fetch")
        and cfg.service_enabled("platform_api")
        and cfg.technology_enabled(fetch_technology)
        and not await asyncio.to_thread(adapter.health_check)
    ):
        raise ValidationError(f"adapter {cmd.platform} failed health check")

    packets: list[ResearchPacket] = []
    for topic, purpose_names in cmd.topics:
        for n in purpose_names:
            if n not in purposes:
                raise ValidationError(f"unknown purpose: {n!r}")
        merged = merge_purposes(purposes, list(purpose_names))
        scoring_weights = resolve_scoring_weights(cfg, merged)
        search_topic = enrich_query(topic, merged.method)
        timings: dict = {"stage_timings": []}
        backends = available_backends(data_dir, cfg=cfg)
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
