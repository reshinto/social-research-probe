"""Abstract base class and result dataclass for corroboration providers.

What: Defines the contract (CorroborationProvider) that every provider must fulfil
and the data structure (CorroborationResult) that all providers return.

Why: A single ABC ensures the host (host.py) can call any provider interchangeably
without knowing its implementation details.

Who calls it: corroboration/registry.py (for type-checking), corroboration/host.py
(consumes CorroborationResult), and individual provider modules (inherit from
CorroborationProvider).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class CorroborationResult:
    """Result of running a single claim through one corroboration provider.

    Lifecycle: created by a provider's corroborate() call and consumed by
    the host's aggregate_verdict() helper and corroborate_claim() function.

    Attributes:
        verdict: One of 'supported', 'refuted', or 'inconclusive'.
        confidence: Float in [0.0, 1.0] — how confident the provider is in the verdict.
        reasoning: Human-readable explanation of the verdict.
        sources: List of source URLs or text snippets used as evidence.
        provider_name: Name of the provider that produced this result.
    """

    verdict: str  # 'supported' | 'refuted' | 'inconclusive'
    confidence: float
    reasoning: str
    sources: list[str] = field(default_factory=list)
    provider_name: str = ""


class CorroborationProvider(ABC):
    """Abstract base class that all corroboration providers must implement.

    Purpose: Provides a uniform interface so the host can run any provider
    without coupling to its internals.

    Lifecycle: Subclasses are instantiated by get_provider() in registry.py and
    passed to corroborate_claim() in host.py.

    ABC contract: subclasses MUST implement health_check() and corroborate().
    """

    name: ClassVar[str]

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if this provider is configured and reachable.

        Returns:
            True when the provider has everything it needs (API key, network,
            subprocess) to accept corroborate() calls; False otherwise.
        """
        ...

    @abstractmethod
    async def corroborate(self, claim) -> CorroborationResult:
        """Check whether the claim is supported by external evidence.

        Args:
            claim: A Claim dataclass instance (from validation/claims.py)
                to corroborate. The provider reads claim.text and optionally
                claim.source_text.

        Returns:
            A CorroborationResult with verdict, confidence, and reasoning
            filled in by the provider.

        Raises:
            AdapterError: if the provider encounters a transient failure
                (network error, bad API response, etc.).
        """
        ...
