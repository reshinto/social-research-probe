"""Platform adapters: base protocol, registry, and platform-specific implementations."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from social_research_probe.platforms.state import PipelineState

from social_research_probe.utils.core.types import EngagementMetrics, FetchLimits, RawItem


class PlatformClient(ABC):
    """Shared contract for every platform regardless of access type."""

    name: ClassVar[str]

    @abstractmethod
    def health_check(self) -> bool: ...


class SearchClient(PlatformClient):
    """API-based platform: discovers content by search query."""

    default_limits: ClassVar[FetchLimits]

    @abstractmethod
    def find_by_topic(self, topic: str, limits: FetchLimits) -> list[RawItem]: ...

    @abstractmethod
    async def fetch_item_details(self, items: list[RawItem]) -> list[RawItem]: ...


class FetchClient(PlatformClient):
    """URL-based platform: pulls content from a known URL."""

    @abstractmethod
    async def fetch(self, url: str) -> list[RawItem]: ...


class BaseStage(ABC):
    """A single named stage in a research pipeline."""

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState: ...

    @abstractmethod
    def stage_name(self) -> str: ...

    def _is_enabled(self, state: PipelineState) -> bool:
        from social_research_probe.config import load_active_config

        return load_active_config().stage_enabled(state.platform_type, self.stage_name())


class BaseResearchPlatform(ABC):
    """Orchestrates an ordered list of stages for one platform type."""

    @abstractmethod
    def stages(self) -> list[BaseStage]: ...

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState: ...


async def run_stages(platform: BaseResearchPlatform, state: PipelineState) -> PipelineState:
    """Execute all enabled stages of a platform pipeline in order."""
    start = time.monotonic()
    name = type(platform).__name__
    from social_research_probe.utils.display.progress import log

    log(f"[PLATFORM][{name}] starting")
    for stage in platform.stages():
        if stage._is_enabled(state):
            state = await stage.execute(state)
    log(f"[PLATFORM][{name}] done in {time.monotonic() - start:.2f}s")
    return state


_concrete_pipelines: dict[str, type] | None = None


def _get_concrete_pipelines() -> dict[str, type]:
    global _concrete_pipelines
    if _concrete_pipelines is None:
        from social_research_probe.platforms.youtube.pipeline import YouTubePipeline

        _concrete_pipelines = {"youtube": YouTubePipeline}
    return _concrete_pipelines


def __getattr__(name: str):
    if name == "PIPELINES":
        from social_research_probe.platforms.all.pipeline import AllPlatformsPipeline

        return {**_get_concrete_pipelines(), "all": AllPlatformsPipeline}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PIPELINES",
    "BaseResearchPlatform",
    "BaseStage",
    "EngagementMetrics",
    "FetchClient",
    "FetchLimits",
    "PlatformClient",
    "RawItem",
    "SearchClient",
    "run_stages",
]
