"""AllPlatformsPipeline: run every registered platform pipeline concurrently."""

from __future__ import annotations

import asyncio
from dataclasses import replace

from social_research_probe.platforms.state import PipelineState


async def _run_one(name: str, pipeline_cls: type, state: PipelineState) -> tuple[str, dict]:
    from social_research_probe.platforms.registry import get_client

    platform_config = state.inputs.get("platform_config", {})
    adapter = get_client(name, platform_config)
    platform_inputs = {**state.inputs, "adapter": adapter}
    platform_state = replace(state, platform_type=name, inputs=platform_inputs, outputs={})
    result = await pipeline_cls().run(platform_state)
    return name, result.outputs.get("report", {})


class AllPlatformsPipeline:
    """Runs all concrete platform pipelines concurrently and aggregates their reports."""

    async def run(self, state: PipelineState) -> PipelineState:
        from social_research_probe.platforms import PIPELINES

        concrete = {k: v for k, v in PIPELINES.items() if k != "all"}
        results = await asyncio.gather(
            *(_run_one(name, pipeline_cls, state) for name, pipeline_cls in concrete.items())
        )
        state.outputs["report"] = {"platforms": dict(results)}
        return state
