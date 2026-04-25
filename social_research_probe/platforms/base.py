"""Platform base classes: client contracts, pipeline stages, and domain types."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from social_research_probe.platforms.state import PipelineState

from social_research_probe.utils.core.types import MetricMap


@dataclass(frozen=True)
class FetchLimits:
    """Search-time fetch limits shared by all platform adapters."""

    max_items: int = 20
    recency_days: int | None = 90


@dataclass(frozen=True)
class RawItem:
    """Normalised raw content item returned by a platform adapter."""

    id: str
    url: str
    title: str
    author_id: str
    author_name: str
    published_at: datetime
    metrics: MetricMap
    text_excerpt: str | None
    thumbnail: str | None
    extras: MetricMap


@dataclass(frozen=True)
class EngagementMetrics:
    """Derived numeric signals computed from one or more raw items."""

    views: int | None
    likes: int | None
    comments: int | None
    upload_date: datetime | None
    view_velocity: float | None
    engagement_ratio: float | None
    comment_velocity: float | None
    cross_channel_repetition: float | None
    raw: MetricMap = field(default_factory=dict)


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


async def run_stages(
    platform: BaseResearchPlatform, state: PipelineState
) -> PipelineState:
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
