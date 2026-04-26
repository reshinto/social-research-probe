"""Top-level research orchestrator: topic loop and report assembly."""

from __future__ import annotations

import os

from social_research_probe.utils.core.research_command_parser import ParsedRunResearch
from social_research_probe.config import load_active_config
from social_research_probe.platforms import PIPELINES
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.core.types import (
    AdapterConfig,
    MultiResearchReport,
    ResearchReport,
)
from social_research_probe.utils.display.fast_mode import (
    FAST_MODE_TOP_N,
    fast_mode_enabled,
)
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.purposes import registry as purpose_registry
from social_research_probe.utils.purposes.merge import MergedPurpose, merge_purposes


def _maybe_register_fake() -> None:
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        importlib.import_module("tests.fixtures.fake_youtube")


def _build_platform_config(cmd: ParsedRunResearch) -> AdapterConfig:
    cfg = load_active_config()
    platform_cfg = {**cfg.platform_defaults(cmd.platform)}
    if fast_mode_enabled():
        platform_cfg["enrich_top_n"] = min(int(platform_cfg.get("enrich_top_n", 5)), FAST_MODE_TOP_N)
    return platform_cfg


def _resolve_purposes(
    purpose_names: tuple[str, ...],
    purposes: dict,
) -> MergedPurpose:
    for n in purpose_names:
        if n not in purposes:
            raise ValidationError(f"unknown purpose: {n!r}")
    return merge_purposes(purposes, list(purpose_names))


def _build_state(
    topic: str,
    merged: MergedPurpose,
    cmd: ParsedRunResearch,
    platform_config: AdapterConfig,
) -> PipelineState:
    return PipelineState(
        platform_type=cmd.platform,
        cmd=cmd,
        cache=None,
        platform_config=dict(platform_config),
        inputs={
            "topic": topic,
            "purpose_names": list(merged.names),
            "merged_purpose": merged,
        },
    )


async def run_pipeline(
    cmd: ParsedRunResearch,
) -> ResearchReport | MultiResearchReport:
    _maybe_register_fake()

    purposes = purpose_registry.load()["purposes"]
    platform_config = _build_platform_config(cmd)

    reports = []
    for topic, purpose_names in cmd.topics:
        merged = _resolve_purposes(purpose_names, purposes)
        state = _build_state(topic, merged, cmd, platform_config)
        state = await PIPELINES[cmd.platform]().run(state)
        report = state.outputs.get("report", {})
        reports.append(report)

    return reports[0] if len(reports) == 1 else {"multi": reports}
