"""Abstract base classes for pipeline stages and research platforms."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from social_research_probe.technologies.base import HealthCheckResult

if TYPE_CHECKING:
    from social_research_probe.platform.state import PipelineState
    from social_research_probe.technologies.base import BaseTechnology


class BaseStage(ABC):
    """A single named stage in a research pipeline.

    Each stage reads from and writes to PipelineState, enabling
    sequential composition inside BaseResearchPlatform.run().
    """

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        """Execute stage logic against state; return updated state."""

    @abstractmethod
    def stage_name(self) -> str:
        """Return the stable identifier for this stage (used in config + logs)."""

    def _is_enabled(self, state: PipelineState) -> bool:
        """Return True iff the stage gate is enabled in config."""
        return state.cfg.stage_enabled(self.stage_name())  # type: ignore[union-attr]


class BaseResearchPlatform(ABC):
    """Orchestrates an ordered list of stages for one platform type.

    Calls stages sequentially; logs platform start/end with timing.
    """

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """Execute all stages in order; return the final state."""

    @abstractmethod
    def stages(self) -> list[BaseStage]:
        """Return the ordered list of stage instances."""

    async def _run_stages(self, state: PipelineState) -> PipelineState:
        """Execute each stage sequentially, skipping disabled ones."""
        start = time.monotonic()
        name = type(self).__name__
        from social_research_probe.utils.progress import log

        log(f"[PLATFORM][{name}] starting")
        for stage in self.stages():
            if stage._is_enabled(state):
                state = await stage.execute(state)
        log(f"[PLATFORM][{name}] done in {time.monotonic() - start:.2f}s")
        return state

    async def health_check_all(
        self,
        state: PipelineState,
    ) -> dict[str, HealthCheckResult]:
        """Run each unique technology health_check_key exactly once.

        Handles both async technologies (returning HealthCheckResult) and
        legacy sync runners (returning bool) transparently.
        """
        import asyncio as _asyncio

        seen: dict[str, HealthCheckResult] = {}
        for stage in self.stages():
            for tech in self._collect_technologies(stage, state):
                key = tech.health_check_key
                if not key or key in seen:
                    continue
                result = tech.health_check()
                if _asyncio.iscoroutine(result):
                    seen[key] = await result
                else:
                    seen[key] = HealthCheckResult(
                        key=key, healthy=bool(result), message="ok"
                    )
        return seen

    def _collect_technologies(
        self,
        stage: BaseStage,
        state: PipelineState,
    ) -> list[BaseTechnology]:
        """Override in subclasses to enumerate technologies from stage services."""
        return []
