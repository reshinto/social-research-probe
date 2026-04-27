"""Corroboration services: registry, provider helpers, and claim orchestration."""

from __future__ import annotations

import asyncio
import sys
from collections import Counter

from social_research_probe.config import Config
from social_research_probe.technologies.corroborates.base import (
    CorroborationProvider,
    CorroborationResult,
)
from social_research_probe.utils.caching.pipeline_cache import (
    corroboration_cache,
    get_json,
    hash_key,
    set_json,
)
from social_research_probe.utils.core.errors import ValidationError

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[CorroborationProvider]] = {}


def register(cls: type[CorroborationProvider]) -> type[CorroborationProvider]:
    """Class decorator that adds cls to the global registry."""
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_provider(name: str) -> CorroborationProvider:
    """Instantiate and return the named provider."""
    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown corroboration provider: {name!r} (registered: {known})")
    return _REGISTRY[name]()


def list_providers() -> list[str]:
    """Return a sorted list of registered provider names."""
    return sorted(_REGISTRY.keys())


def ensure_providers_registered() -> None:
    """Import concrete provider modules so their @register decorators run."""
    import importlib

    for module in ("exa", "brave", "tavily", "llm_search"):
        try:
            importlib.import_module(f"social_research_probe.technologies.corroborates.{module}")
        except ImportError:
            continue


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------


def auto_mode_providers(cfg: Config) -> tuple[str, ...]:
    """Return ordered provider names to try in auto mode."""
    return tuple(
        name for name in ("exa", "brave", "tavily", "llm_search") if cfg.technology_enabled(name)
    )


# ---------------------------------------------------------------------------
# Claim orchestration
# ---------------------------------------------------------------------------


def aggregate_verdict(results: list[CorroborationResult]) -> tuple[str, float]:
    """Compute combined verdict and confidence from provider results.

    Majority vote; ties resolve to 'inconclusive'. Confidence is
    weighted average where each weight equals the provider's confidence.
    """
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
    import dataclasses

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
