"""Corroboration technology adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse

from social_research_probe.technologies import BaseTechnology


@dataclass
class CorroborationResult:
    """Result of running a single claim through one corroboration provider."""

    verdict: str  # 'supported' | 'refuted' | 'inconclusive'
    confidence: float
    reasoning: str
    sources: list[str] = field(default_factory=list)
    provider_name: str = ""


class CorroborationProvider(ABC):
    """Abstract base class that all corroboration providers must implement."""

    name: ClassVar[str]

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    async def corroborate(self, claim) -> CorroborationResult: ...


VIDEO_HOST_DOMAINS: frozenset[str] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "vimeo.com",
        "www.vimeo.com",
        "tiktok.com",
        "www.tiktok.com",
        "m.tiktok.com",
        "rumble.com",
        "www.rumble.com",
        "dailymotion.com",
        "www.dailymotion.com",
        "twitch.tv",
        "www.twitch.tv",
        "m.twitch.tv",
    }
)


def _host(url: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    return host or None


def is_video_url(url: str) -> bool:
    """True if url is hosted on a known video platform."""
    host = _host(url)
    if host is None:
        return False
    return host in VIDEO_HOST_DOMAINS


def is_self_source(result_url: str, source_url: str | None) -> bool:
    """True if result_url is the same as source_url or shares its host."""
    if not source_url:
        return False
    if result_url == source_url:
        return True
    r_host = _host(result_url)
    s_host = _host(source_url)
    if r_host is None or s_host is None:
        return False
    return r_host == s_host


def filter_results(
    raw_results: list[dict],
    source_url: str | None,
    *,
    url_key: str = "url",
) -> tuple[list[dict], int, int]:
    """Drop self-source and video-hosting-domain results from a provider payload."""
    kept: list[dict] = []
    self_excluded = 0
    video_excluded = 0
    for item in raw_results:
        url = str(item.get(url_key) or "")
        if not url:
            kept.append(item)
            continue
        if is_self_source(url, source_url):
            self_excluded += 1
            continue
        if is_video_url(url):
            video_excluded += 1
            continue
        kept.append(item)
    return kept, self_excluded, video_excluded


class CorroborationHostTech(BaseTechnology[object, dict]):
    """Technology wrapper for corroborating a single item's claim."""

    name: ClassVar[str] = "corroboration_host"

    def __init__(self, providers: list[str]):
        super().__init__()
        self.providers = providers

    async def _execute(self, input_data: object) -> dict:
        from social_research_probe.services.corroborating import corroborate_claim
        from social_research_probe.technologies.validation.claim_extractor import Claim

        title = input_data.get("title", "") if isinstance(input_data, dict) else str(input_data)
        url = input_data.get("url") if isinstance(input_data, dict) else None
        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        return await corroborate_claim(claim, self.providers)
