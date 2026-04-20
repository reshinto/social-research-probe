"""Abstract base class and result dataclass for corroboration backends.

What: Defines the contract (CorroborationBackend) that every backend must fulfil
and the data structure (CorroborationResult) that all backends return.

Why: A single ABC ensures the host (host.py) can call any backend interchangeably
without knowing its implementation details.

Who calls it: corroboration/registry.py (for type-checking), corroboration/host.py
(consumes CorroborationResult), and individual backend modules (inherit from
CorroborationBackend).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class CorroborationResult:
    """Result of running a single claim through one corroboration backend.

    Lifecycle: created by a backend's corroborate() call and consumed by
    the host's aggregate_verdict() helper and corroborate_claim() function.

    Attributes:
        verdict: One of 'supported', 'refuted', or 'inconclusive'.
        confidence: Float in [0.0, 1.0] — how confident the backend is in the verdict.
        reasoning: Human-readable explanation of the verdict.
        sources: List of source URLs or text snippets used as evidence.
        backend_name: Name of the backend that produced this result.
    """

    verdict: str  # 'supported' | 'refuted' | 'inconclusive'
    confidence: float
    reasoning: str
    sources: list[str] = field(default_factory=list)
    backend_name: str = ""


class CorroborationBackend(ABC):
    """Abstract base class that all corroboration backends must implement.

    Purpose: Provides a uniform interface so the host can run any backend
    without coupling to its internals.

    Lifecycle: Subclasses are instantiated by get_backend() in registry.py and
    passed to corroborate_claim() in host.py.

    ABC contract: subclasses MUST implement health_check() and corroborate().
    """

    name: ClassVar[str]

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if this backend is configured and reachable.

        Returns:
            True when the backend has everything it needs (API key, network,
            subprocess) to accept corroborate() calls; False otherwise.
        """
        ...

    @abstractmethod
    async def corroborate(self, claim) -> CorroborationResult:
        """Check whether the claim is supported by external evidence.

        Args:
            claim: A Claim dataclass instance (from validation/claims.py)
                to corroborate. The backend reads claim.text and optionally
                claim.source_text.

        Returns:
            A CorroborationResult with verdict, confidence, and reasoning
            filled in by the backend.

        Raises:
            AdapterError: if the backend encounters a transient failure
                (network error, bad API response, etc.).
        """
        ...
