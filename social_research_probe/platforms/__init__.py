"""Platform adapters: base protocol, registry, and platform-specific implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from social_research_probe.platforms.state import PipelineState

from social_research_probe.utils.core.types import (
    EngagementMetrics,
    FetchLimits,
    RawItem,
)
from social_research_probe.utils.display.progress import log_with_time


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

    disable_cache_for_technologies: ClassVar[list[str]] = []

    @log_with_time("[srp] {state.platform_type}/{self.stage_name}: execute")
    async def run(self, state: PipelineState) -> PipelineState:
        """Set stage cache overrides, time execution, then return result."""
        from social_research_probe.utils.caching.pipeline_cache import (
            disable_cache_for_technologies,
        )

        disable_cache_for_technologies.set(self.disable_cache_for_technologies)
        return await self.execute(state)

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState: ...

    @property
    @abstractmethod
    def stage_name(self) -> str: ...

    def _is_enabled(self, state: PipelineState) -> bool:
        from social_research_probe.config import load_active_config

        return load_active_config().stage_enabled(state.platform_type, self.stage_name)


class BaseResearchPlatform(ABC):
    """Orchestrates an ordered list of stages for one platform type."""

    @abstractmethod
    def stages(self) -> list[BaseStage]: ...

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState: ...


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
]
