"""Top-level research orchestrator: topic loop and report assembly."""

from __future__ import annotations

import os

from social_research_probe.config import load_active_config
from social_research_probe.platforms import PIPELINES
from social_research_probe.platforms.state import PipelineState
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.research_command_parser import ParsedRunResearch
from social_research_probe.utils.core.types import (
    AdapterConfig,
    MultiResearchReport,
    ResearchReport,
)
from social_research_probe.utils.display.fast_mode import (
    FAST_MODE_TOP_N,
    fast_mode_enabled,
)
from social_research_probe.utils.purposes import registry as purpose_registry
from social_research_probe.utils.purposes.merge import MergedPurpose, merge_purposes


def _maybe_register_fake() -> None:
    """Register the fake platform only when the current run needs test/demo behavior.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _maybe_register_fake()
        Output:
            None
    """
    if os.environ.get("SRP_TEST_USE_FAKE_YOUTUBE") == "1":
        import importlib

        fake = importlib.import_module("tests.fixtures.fake_youtube")
        from social_research_probe.services.sourcing.youtube import YouTubeSourcingService

        YouTubeSourcingService.execute_one = fake.fake_execute_one


def _build_platform_config(cmd: ParsedRunResearch) -> AdapterConfig:
    """Build the small payload that carries enrich_top_n through this workflow.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        cmd: Parsed command object or lightweight namespace for the current run.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _build_platform_config(
                cmd=argparse.Namespace(platform="youtube"),
            )
        Output:
            Config(data_dir=Path(".skill-data"))
    """
    cfg = load_active_config()
    platform_cfg = {**cfg.platform_defaults(cmd.platform)}
    if fast_mode_enabled():
        platform_cfg["enrich_top_n"] = min(
            int(platform_cfg.get("enrich_top_n", 5)), FAST_MODE_TOP_N
        )
    return platform_cfg


def _resolve_purposes(
    purpose_names: tuple[str, ...],
    purposes: dict,
) -> MergedPurpose:
    """Resolve requested purpose names into merged purpose definitions.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        purpose_names: Purpose name or purpose definitions that shape the research goal.
        purposes: Purpose name or purpose definitions that shape the research goal.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _resolve_purposes(
                purpose_names=("Opportunity Map",),
                purposes=[{"name": "Opportunity Map"}],
            )
        Output:
            "AI safety"
    """
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
    """Build build state in the shape consumed by the next project step.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        topic: Research topic text or existing topic list used for classification and suggestions.
        merged: Merged purpose or report data produced by earlier normalization.
        cmd: Parsed command object or lightweight namespace for the current run.
        platform_config: Configuration or context values that control this run.

    Returns:
        The same PipelineState instance after this stage has published its output.

    Examples:
        Input:
            _build_state(
                topic="AI safety",
                merged="AI safety",
                cmd=argparse.Namespace(platform="youtube"),
                platform_config={"enabled": True},
            )
        Output:
            PipelineState(platform_type="youtube", cmd=None, cache=None)
    """
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
    """Document the run pipeline rule at the boundary where callers use it.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        cmd: Parsed command object or lightweight namespace for the current run.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            await run_pipeline(
                cmd=argparse.Namespace(platform="youtube"),
            )
        Output:
            "AI safety"
    """
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
