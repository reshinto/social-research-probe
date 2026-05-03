"""AllPlatformsPipeline: run every registered platform pipeline concurrently."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from social_research_probe.platforms.state import PipelineState


async def _run_one(name: str, pipeline_cls: type, state: PipelineState) -> tuple[str, dict]:
    """Document the run one rule at the boundary where callers use it.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.
        pipeline_cls: Pipeline class selected for one platform run.
        state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            await _run_one(
                name="AI safety",
                pipeline_cls="AI safety",
                state=PipelineState(platform_type="youtube", cmd=None, cache=None),
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    platform_state = replace(state, platform_type=name, inputs=dict(state.inputs), outputs={})
    result = await pipeline_cls().run(platform_state)
    return name, result.outputs.get("report", {})


class AllPlatformsPipeline:
    """Runs all concrete platform pipelines concurrently and aggregates their reports.

    Examples:
        Input:
            AllPlatformsPipeline
        Output:
            AllPlatformsPipeline
    """

    async def run(self, state: PipelineState) -> PipelineState:
        """Document the run rule at the boundary where callers use it.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                await run(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
        from social_research_probe.platforms import PIPELINES

        concrete = {k: v for k, v in PIPELINES.items() if k != "all"}
        results = await asyncio.gather(
            *(_run_one(name, pipeline_cls, state) for name, pipeline_cls in concrete.items())
        )
        state.outputs["report"] = {"platforms": dict(results)}
        return state
