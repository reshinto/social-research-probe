"""Platform adapter contract. All per-platform logic lives in subpackages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from social_research_probe.types import MetricMap


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
class SignalSet:
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


@dataclass(frozen=True)
class TrustHints:
    """Non-engagement trust indicators extracted from an item or channel."""

    account_age_days: int | None
    verified: bool | None
    subscriber_count: int | None
    upload_cadence_days: float | None
    citation_markers: list[str]


class PlatformAdapter(ABC):
    """Contract that every content-source adapter must implement."""

    name: ClassVar[str]
    default_limits: ClassVar[FetchLimits]

    @abstractmethod
    def health_check(self) -> bool:
        """Return True when the adapter is configured and callable."""
        ...

    @abstractmethod
    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]:
        """Fetch raw items for a query topic subject to the provided limits."""
        ...

    @abstractmethod
    async def enrich(self, items: list[RawItem]) -> list[RawItem]:
        """Hydrate raw items with additional metrics or channel metadata."""
        ...

    @abstractmethod
    def to_signals(self, items: list[RawItem]) -> list[SignalSet]:
        """Convert raw items into the numeric signals used by scoring and stats."""
        ...

    @abstractmethod
    def trust_hints(self, item: RawItem) -> TrustHints:
        """Extract trust-oriented metadata for one item."""
        ...

    @abstractmethod
    def url_normalize(self, url: str) -> str:
        """Return a canonical URL string for deduplication and display."""
        ...

    def fetch_text_for_claim_extraction(self, item: RawItem) -> str | None:
        """Optionally provide claim-extraction text for one item."""
        return None
