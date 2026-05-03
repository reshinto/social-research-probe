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
    """Shared contract for every platform regardless of access type.

    Examples:
        Input:
            PlatformClient
        Output:
            PlatformClient
    """

    name: ClassVar[str]

    @abstractmethod
    def health_check(self) -> bool:
        """Report whether this client or provider is usable before it is selected.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                health_check()
            Output:
                True
        """
        ...


class SearchClient(PlatformClient):
    """API-based platform: discovers content by search query.

    Examples:
        Input:
            SearchClient
        Output:
            SearchClient
    """

    default_limits: ClassVar[FetchLimits]

    @abstractmethod
    def find_by_topic(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        """Find platform items that match a research topic.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Args:
            topic: Research topic text or existing topic list used for classification and suggestions.
            limits: Count, database id, index, or limit that bounds the work being performed.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                find_by_topic(
                    topic="AI safety",
                    limits=3,
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        ...

    @abstractmethod
    async def fetch_item_details(self, items: list[RawItem]) -> list[RawItem]:
        """Fetch item details without exposing provider details to callers.

        Platform orchestration uses this contract to run different platforms without leaking platform-
        specific state into callers.

        Args:
            items: Ordered source items being carried through the current pipeline step.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await fetch_item_details(
                    items=[{"title": "Example", "url": "https://youtu.be/demo"}],
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        ...


class FetchClient(PlatformClient):
    """URL-based platform: pulls content from a known URL.

    Examples:
        Input:
            FetchClient
        Output:
            FetchClient
    """

    @abstractmethod
    async def fetch(self, url: str) -> list[RawItem]:
        """Fetch platform items from a known URL or provider request.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Args:
            url: Stable source identifier or URL used to join records across stages and exports.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await fetch(
                    url="https://youtu.be/abc123",
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        ...


class BaseStage(ABC):
    """A single named stage in a research pipeline.

    Examples:
        Input:
            BaseStage
        Output:
            BaseStage()
    """

    disable_cache_for_technologies: ClassVar[list[str]] = []

    @log_with_time("[srp] {state.platform_type}/{self.stage_name}: execute")
    async def run(self, state: PipelineState) -> PipelineState:
        """Set stage cache overrides, time execution, then return result.

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
        from social_research_probe.utils.caching.pipeline_cache import (
            disable_cache_for_technologies,
        )

        disable_cache_for_technologies.set(self.disable_cache_for_technologies)
        return await self.execute(state)

    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        """Run the base stage and save its result on PipelineState.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            The same PipelineState instance after this stage has published its output.

        Examples:
            Input:
                await execute(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                PipelineState(platform_type="youtube", cmd=None, cache=None)
        """
        ...

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Return the stable stage key used by config and PipelineState.

        Config, cache, and PipelineState all key off this value, so it is kept beside the stage
        implementation that owns it.

        Returns:
            The configured stage name setting.

        Examples:
            Input:
                stage.stage_name
            Output:
                "base"
        """
        ...

    def _is_enabled(self, state: PipelineState) -> bool:
        """Return whether is enabled is true for the input.

        Platform orchestration uses this contract to run different platforms without leaking platform-
        specific state into callers.

        Args:
            state: PipelineState carrying config, inputs, and outputs accumulated by earlier stages.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                _is_enabled(
                    state=PipelineState(platform_type="youtube", cmd=None, cache=None),
                )
            Output:
                True
        """
        from social_research_probe.config import load_active_config

        return load_active_config().stage_enabled(state.platform_type, self.stage_name)


class BaseResearchPlatform(ABC):
    """Orchestrates an ordered list of stages for one platform type.

    Examples:
        Input:
            BaseResearchPlatform
        Output:
            BaseResearchPlatform
    """

    @abstractmethod
    def stages(self) -> list[BaseStage]:
        """Return the ordered stage groups that define this pipeline.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                stages()
            Output:
                {"youtube": {"fetch": True}}
        """
        ...

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """Run the configured pipeline or command and return its result.

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
        ...


_concrete_pipelines: dict[str, type] | None = None


def _get_concrete_pipelines() -> dict[str, type]:
    """Build the small payload that carries youtube through this workflow.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _get_concrete_pipelines()
        Output:
            {"enabled": True}
    """
    global _concrete_pipelines
    if _concrete_pipelines is None:
        from social_research_probe.platforms.youtube import YouTubePipeline

        _concrete_pipelines = {"youtube": YouTubePipeline}
    return _concrete_pipelines


def __getattr__(name: str):
    """Build the small payload that carries all through this workflow.

    Platform orchestration code uses this contract to run different platforms without leaking
    platform-specific state into callers.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            __getattr__(
                name="AI safety",
            )
        Output:
            "AI safety"
    """
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
