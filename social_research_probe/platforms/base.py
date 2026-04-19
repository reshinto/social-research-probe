"""Platform adapter contract. All per-platform logic lives in subpackages."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar


@dataclass(frozen=True)
class FetchLimits:
    max_items: int = 20
    recency_days: int | None = 90


@dataclass(frozen=True)
class RawItem:
    id: str
    url: str
    title: str
    author_id: str
    author_name: str
    published_at: datetime
    metrics: dict[str, Any]
    text_excerpt: str | None
    thumbnail: str | None
    extras: dict[str, Any]


@dataclass(frozen=True)
class SignalSet:
    views: int | None
    likes: int | None
    comments: int | None
    upload_date: datetime | None
    view_velocity: float | None
    engagement_ratio: float | None
    comment_velocity: float | None
    cross_channel_repetition: float | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrustHints:
    account_age_days: int | None
    verified: bool | None
    subscriber_count: int | None
    upload_cadence_days: float | None
    citation_markers: list[str]


class PlatformAdapter(ABC):
    name: ClassVar[str]
    default_limits: ClassVar[FetchLimits]

    @abstractmethod
    def health_check(self) -> bool: ...  # pragma: no cover

    @abstractmethod
    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: ...  # pragma: no cover

    @abstractmethod
    def enrich(self, items: list[RawItem]) -> list[RawItem]: ...  # pragma: no cover

    @abstractmethod
    def to_signals(self, items: list[RawItem]) -> list[SignalSet]: ...  # pragma: no cover

    @abstractmethod
    def trust_hints(self, item: RawItem) -> TrustHints: ...  # pragma: no cover

    @abstractmethod
    def url_normalize(self, url: str) -> str: ...  # pragma: no cover

    def fetch_text_for_claim_extraction(self, item: RawItem) -> str | None:
        return None
