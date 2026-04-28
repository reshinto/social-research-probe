"""Corroboration technology adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.caching.pipeline_cache import (
    corroboration_cache,
    get_json,
    hash_key,
    set_json,
)
from social_research_probe.utils.core.errors import ValidationError


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


_REGISTRY: dict[str, type[CorroborationProvider]] = {}


def register(cls: type[CorroborationProvider]) -> type[CorroborationProvider]:
    """Class decorator that adds cls to the global registry."""
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_provider(name: str) -> CorroborationProvider:
    """Instantiate and return the named provider if its technology is enabled."""
    from social_research_probe.config import load_active_config

    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown corroboration provider: {name!r} (registered: {known})")
    cfg = load_active_config()
    if not cfg.technology_enabled(name):
        raise ValidationError(f"corroboration provider {name!r} is not enabled")
    return _REGISTRY[name]()


def list_providers() -> list[str]:
    """Return a sorted list of registered provider names that are technology-enabled."""
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    return sorted(name for name in _REGISTRY.keys() if cfg.technology_enabled(name))


def ensure_providers_registered() -> None:
    """Import concrete provider modules so their @register decorators run."""
    import importlib

    for module in ("exa", "brave", "tavily", "llm_search"):
        try:
            importlib.import_module(f"social_research_probe.technologies.corroborates.{module}")
        except ImportError:
            continue


def aggregate_verdict(results: list[CorroborationResult]) -> tuple[str, float]:
    """Compute combined verdict and confidence from provider results.

    Majority vote; ties resolve to 'inconclusive'. Confidence is
    weighted average where each weight equals the provider's confidence.
    """
    from collections import Counter

    if not results:
        return ("inconclusive", 0.0)

    counts: Counter[str] = Counter(r.verdict for r in results)
    top_verdicts = counts.most_common()

    if len(top_verdicts) >= 2 and top_verdicts[0][1] == top_verdicts[1][1]:
        winner = "inconclusive"
    else:
        winner = top_verdicts[0][0]

    total_weight = sum(r.confidence for r in results)
    avg_confidence = (
        sum(r.confidence * r.confidence for r in results) / total_weight
        if total_weight > 0.0
        else 0.0
    )
    avg_confidence = max(0.0, min(1.0, avg_confidence))

    return (winner, avg_confidence)


async def corroborate_claim(claim, provider_names: list[str]) -> dict:
    """Run a claim through multiple providers concurrently and aggregate results.

    Results cached by (claim_text, sorted_providers).
    """
    import asyncio
    import dataclasses
    import sys

    normalized_providers = list(dict.fromkeys(provider_names))
    cache = corroboration_cache()
    cache_key = hash_key("claim", claim.text, ",".join(sorted(normalized_providers)))
    cached = get_json(cache, cache_key)
    if cached is not None:
        return cached

    async def _call_provider(provider_name: str) -> CorroborationResult | None:
        try:
            provider = get_provider(provider_name)
            return await provider.corroborate(claim)
        except Exception as exc:
            print(f"[corroboration] provider {provider_name!r} failed: {exc}", file=sys.stderr)
            return None

    outcomes = await asyncio.gather(
        *[_call_provider(name) for name in normalized_providers],
        return_exceptions=False,
    )
    collected = [r for r in outcomes if r is not None]
    verdict, confidence = aggregate_verdict(collected)

    result = {
        "claim_text": claim.text,
        "results": [dataclasses.asdict(r) for r in collected],
        "aggregate_verdict": verdict,
        "aggregate_confidence": confidence,
    }
    set_json(cache, cache_key, result)
    return result


class CorroborationHostTech(BaseTechnology[object, dict]):
    """Technology wrapper for corroborating a single item's claim."""

    name: ClassVar[str] = "corroboration_host"

    def __init__(self, providers: list[str]):
        super().__init__()
        self.providers = providers

    async def _execute(self, input_data: object) -> dict:
        from social_research_probe.technologies.validation.claim_extractor import Claim

        title = input_data.get("title", "") if isinstance(input_data, dict) else str(input_data)
        url = input_data.get("url") if isinstance(input_data, dict) else None
        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        return await corroborate_claim(claim, self.providers)
