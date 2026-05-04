"""Corroboration technology adapters."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.core.errors import ValidationError


@dataclass
class CorroborationResult:
    """Result of running a single claim through one corroboration provider.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            CorroborationResult
        Output:
            CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
    """

    verdict: str  # 'supported' | 'refuted' | 'inconclusive'
    confidence: float
    reasoning: str
    sources: list[str] = field(default_factory=list)
    provider_name: str = ""


class CorroborationProvider(BaseTechnology[object, CorroborationResult]):
    """Abstract base class that all corroboration providers must implement.

    Examples:
        Input:
            CorroborationProvider
        Output:
            CorroborationProvider
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

    @abstractmethod
    async def corroborate(self, claim) -> CorroborationResult:
        """Document the corroborate rule at the boundary where callers use it.

        Extraction, review, corroboration, and reporting all need the same claim shape.

        Args:
            claim: Claim text or claim dictionary being extracted, classified, reviewed, or
                   corroborated.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                await corroborate(
                    claim={"text": "The model reduces latency by 30%."},
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        ...

    async def _execute(self, data: object) -> CorroborationResult:
        """Run this component and return the project-shaped output expected by its service.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        return await self.corroborate(data)


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
    """Return the host.

    Args:
        url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _host(
                url="https://youtu.be/abc123",
            )
        Output:
            "AI safety"
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    return host or None


def is_video_url(url: str) -> bool:
    """True if url is hosted on a known video platform.

    Args:
        url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            is_video_url(
                url="https://youtu.be/abc123",
            )
        Output:
            True
    """
    host = _host(url)
    if host is None:
        return False
    return host in VIDEO_HOST_DOMAINS


def is_self_source(result_url: str, source_url: str | None) -> bool:
    """True if result_url is the same as source_url or shares its host.

    Args:
        result_url: Candidate result URL before video and domain filtering.
        source_url: Stable source identifier or URL used to join records across stages and exports.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            is_self_source(
                result_url="AI safety",
                source_url="https://youtu.be/abc123",
            )
        Output:
            True
    """
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
    """Drop self-source and video-hosting-domain results from a provider payload.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        raw_results: Provider result records before project-level normalization.
        source_url: Stable source identifier or URL used to join records across stages and exports.
        url_key: Provider response key that contains a result URL.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            filter_results(
                raw_results=["AI safety"],
                source_url="https://youtu.be/abc123",
                url_key="AI safety",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Register the implementation in the module registry.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            register()
        Output:
            "AI safety"
    """
    if not hasattr(cls, "name") or not cls.name:
        raise ValueError(f"{cls!r} must define class var `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get_provider(name: str) -> CorroborationProvider:
    """Document the get provider rule at the boundary where callers use it.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            get_provider(
                name="AI safety",
            )
        Output:
            "AI safety"
    """
    from social_research_probe.config import load_active_config

    if name not in _REGISTRY:
        known = sorted(_REGISTRY.keys())
        raise ValidationError(f"unknown corroboration provider: {name!r} (registered: {known})")
    cfg = load_active_config()
    if not cfg.technology_enabled(name):
        raise ValidationError(f"corroboration provider {name!r} is not enabled")
    return _REGISTRY[name]()


def list_providers() -> list[str]:
    """Return a sorted list of registered provider names that are technology-enabled.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            list_providers()
        Output:
            ["AI safety", "model evaluation"]
    """
    from social_research_probe.config import load_active_config

    cfg = load_active_config()
    return sorted(name for name in _REGISTRY if cfg.technology_enabled(name))


def ensure_providers_registered() -> None:
    """Import concrete provider modules so their @register decorators run.

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            ensure_providers_registered()
        Output:
            None
    """
    import importlib

    for module in ("exa", "brave", "tavily", "llm_search"):
        try:
            importlib.import_module(f"social_research_probe.technologies.corroborates.{module}")
        except ImportError:
            continue


def aggregate_verdict(results: list[CorroborationResult]) -> tuple[str, float]:
    """Compute combined verdict and confidence from provider results.

    Majority vote; ties resolve to 'inconclusive'. Confidence is weighted average where each weight
    equals the provider's confidence.

    Args:
        results: Service or technology result being inspected for payload and diagnostics.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            aggregate_verdict(
                results=[ServiceResult(service_name="comments", input_key="demo", tech_results=[])],
            )
        Output:
            ("AI safety", "Find unmet needs")
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

    Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
    failure handling visible at the boundary.

    Args:
        claim: Claim text or claim dictionary being extracted, classified, reviewed, or
               corroborated.
        provider_names: Provider names that should be tried in order.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            await corroborate_claim(
                claim={"text": "The model reduces latency by 30%."},
                provider_names=["AI safety"],
            )
        Output:
            {"enabled": True}
    """
    import asyncio
    import dataclasses
    import sys

    normalized_providers = list(dict.fromkeys(provider_names))

    async def _call_provider(provider_name: str) -> CorroborationResult | None:
        """Return the call provider.

        Corroboration code handles external evidence, so claim shape and provider failure handling stay
        visible here.

        Args:
            provider_name: Provider or runner selected for this operation.

        Returns:
            CorroborationResult with verdict, confidence, reasoning, sources, and provider name.

        Examples:
            Input:
                await _call_provider(
                    provider_name="brave",
                )
            Output:
                CorroborationResult(verdict="supported", confidence=0.82, reasoning="Sources agree.")
        """
        try:
            provider = get_provider(provider_name)
            return await provider.execute(claim)
        except Exception as exc:
            print(f"[corroboration] provider {provider_name!r} failed: {exc}", file=sys.stderr)
            return None

    outcomes = await asyncio.gather(
        *[_call_provider(name) for name in normalized_providers],
        return_exceptions=False,
    )
    collected = [r for r in outcomes if r is not None]
    verdict, confidence = aggregate_verdict(collected)

    return {
        "claim_text": claim.text,
        "results": [dataclasses.asdict(r) for r in collected],
        "aggregate_verdict": verdict,
        "aggregate_confidence": confidence,
    }


class CorroborationHostTech(BaseTechnology[object, dict]):
    """Technology wrapper for corroborating a single item's claim.

    Examples:
        Input:
            CorroborationHostTech
        Output:
            CorroborationHostTech
    """

    name: ClassVar[str] = "corroboration_host"
    enabled_config_key: ClassVar[str] = "corroboration_host"

    def __init__(self, providers: list[str]):
        """Store constructor options used by later method calls.

        Args:
            providers: Provider names selected for corroboration, search, or fallback execution.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                __init__(
                    providers=["AI safety"],
                )
            Output:
                "AI safety"
        """
        super().__init__()
        self.providers = providers

    async def _execute(self, input_data: object) -> dict:
        """Run this component and return the project-shaped output expected by its service.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            input_data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    input_data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                {"enabled": True}
        """
        if not isinstance(input_data, dict):
            return await self._corroborate_title_fallback(str(input_data), None)
        corroborable = self._corroborable_claims(input_data)
        if corroborable:
            return await self._corroborate_from_extracted(input_data, corroborable)
        return await self._corroborate_title_fallback(
            input_data.get("title", ""),
            input_data.get("url"),
        )

    def _corroborable_claims(self, data: dict) -> list[dict]:
        """Document the corroborable claims rule at the boundary where callers use it.

        Extraction, review, corroboration, and reporting all need the same claim shape.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _corroborable_claims(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        from social_research_probe.config import load_active_config

        max_n = int(load_active_config().raw.get("corroboration", {}).get("max_claims_per_item", 5))
        extracted = data.get("extracted_claims") or []
        needs = [c for c in extracted if isinstance(c, dict) and c.get("needs_corroboration")]
        return needs[:max_n]

    async def _corroborate_title_fallback(self, title: str, url: object) -> dict:
        """Document the corroborate title fallback rule at the boundary where callers use it.

        Extraction, review, corroboration, and reporting all need the same claim shape.

        Args:
            title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                   to a provider.
            url: Stable source identifier or URL used to join records across stages and exports.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _corroborate_title_fallback(
                    title="This tool reduces latency by 30%.",
                    url="https://youtu.be/abc123",
                )
            Output:
                {"enabled": True}
        """
        from social_research_probe.technologies.validation.claim_extractor import Claim

        claim = Claim(text=title, source_text=title, index=0, source_url=url)
        return await corroborate_claim(claim, self.providers)

    async def _corroborate_from_extracted(self, data: dict, claims: list[dict]) -> dict:
        """Document the corroborate from extracted rule at the boundary where callers use it.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            claims: Claim records being extracted, reviewed, persisted, or corroborated.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _corroborate_from_extracted(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    claims={"text": "The model reduces latency by 30%."},
                )
            Output:
                {"enabled": True}
        """
        from social_research_probe.technologies.validation.claim_extractor import Claim

        claim_results: list[dict] = []
        for i, c in enumerate(claims):
            claim_obj = Claim(
                text=c["claim_text"],
                source_text=c.get("evidence_text", c["claim_text"]),
                index=i,
                source_url=c.get("source_url"),
            )
            result = await self._try_corroborate(claim_obj)
            if result:
                c["corroboration_status"] = result.get("aggregate_verdict", "inconclusive")
                claim_results.append(result)
        return self._build_claims_result(data, claim_results)

    async def _try_corroborate(self, claim_obj: object) -> dict | None:
        """Return the try corroborate.

        Corroboration code handles external evidence, so claim shape and provider failure handling stay
        visible here.

        Args:
            claim_obj: Claim text or claim dictionary being extracted, classified, reviewed, or
                       corroborated.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _try_corroborate(
                    claim_obj={"text": "The model reduces latency by 30%."},
                )
            Output:
                {"enabled": True}
        """
        try:
            return await corroborate_claim(claim_obj, self.providers)
        except Exception:
            return None

    def _build_claims_result(self, data: dict, claim_results: list[dict]) -> dict:
        """Build build claims result in the shape consumed by the next project step.

        Corroboration code deals with external evidence, so this keeps claim shape, provider calls, and
        failure handling visible at the boundary.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.
            claim_results: Per-claim corroboration results before report aggregation.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _build_claims_result(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                    claim_results={"text": "The model reduces latency by 30%."},
                )
            Output:
                {"enabled": True}
        """
        from collections import Counter

        verdicts = [r.get("aggregate_verdict", "inconclusive") for r in claim_results]
        counts: Counter[str] = Counter(verdicts)
        verdict = "inconclusive"
        if counts:
            top = counts.most_common(2)
            if len(top) == 1 or top[0][1] != top[1][1]:
                verdict = top[0][0]
        confidence = (
            sum(r.get("aggregate_confidence", 0.0) for r in claim_results) / len(claim_results)
            if claim_results
            else 0.0
        )
        return {
            "claim_text": data.get("title", ""),
            "results": claim_results,
            "aggregate_verdict": verdict,
            "aggregate_confidence": confidence,
        }
