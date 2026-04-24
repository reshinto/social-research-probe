"""Abstract base class for all LLM runner implementations.

Why this exists: the pipeline and corroboration host need to call LLMs without
knowing which vendor is behind the call. Every new LLM (Claude, Gemini, a local
model) can be added by subclassing LLMRunner and registering it — no calling
code changes needed.

Who calls it: llm.registry (for type constraints), the pipeline, and the
corroboration host.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from social_research_probe.technologies.llms import AgenticSearchResult


class CapabilityUnavailableError(RuntimeError):
    """Raised when a caller invokes a capability the active runner doesn't support.

    Example: calling ``agentic_search`` on a runner whose
    ``supports_agentic_search`` is False.
    """


class LLMRunner(ABC):
    """Contract that every LLM runner must fulfil.

    Purpose: provide a uniform interface so callers are decoupled from any
    specific LLM vendor or binary.

    Lifecycle: subclasses are registered at import time via the @register
    decorator in llm.registry; the registry instantiates them on demand.

    Who instantiates it: llm.registry.get_runner(), never called directly.

    ABC/protocol fulfilled: ABC with two abstract methods — health_check and run.
    """

    # Each concrete subclass must set this to a unique string key (e.g. "claude").
    # The registry uses this key to look up the runner by name.
    name: ClassVar[str]

    # Opt-in capability flag for runners that can summarise a media URL
    # directly (e.g. Gemini's native YouTube URL ingestion). Default False so
    # consumers can safely call summarize_media() only on runners that flip
    # this to True, without needing runner-specific code paths.
    supports_media_url: ClassVar[bool] = False

    # Opt-in capability flag for runners that can perform an agentic web
    # search using their native tool (Gemini google-search, Claude web_search,
    # Codex --search). Default False — runners that do not support it must
    # leave this untouched so callers can dispatch based on the flag rather
    # than catching CapabilityUnavailableError.
    supports_agentic_search: ClassVar[bool] = False

    async def summarize_media(
        self, url: str, *, word_limit: int = 100, timeout_s: float = 60.0
    ) -> str | None:
        """Summarise the media at ``url`` directly (no transcript required).

        Default returns ``None``; runners opt in by overriding and flipping
        ``supports_media_url`` to True. Callers treat ``None`` as "signal
        unavailable" and continue. Must never raise.
        """
        return None

    async def agentic_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout_s: float = 60.0,
    ) -> AgenticSearchResult:
        """Perform an agentic web search and return a structured payload.

        Runners that support it (flip ``supports_agentic_search`` to True) use
        their vendor-native capability: Gemini's google-search grounding,
        Claude's ``web_search`` tool, Codex's ``--search`` flag. Runners that
        don't support it must leave ``supports_agentic_search`` False; calling
        this method on them raises :class:`CapabilityUnavailableError` so mis-routed
        callers fail loudly instead of silently returning no evidence.

        Args:
            query: The free-text search query (usually a factual claim).
            max_results: Soft cap on citations returned. Runners may return
                fewer.
            timeout_s: Maximum wall-clock time for the vendor call.

        Returns:
            :class:`AgenticSearchResult` with answer, citations, and the
            runner's own name.

        Raises:
            CapabilityUnavailableError: If the runner does not support agentic
                search.
            AdapterError: If the vendor call fails at runtime.
        """
        raise CapabilityUnavailableError(
            f"runner {getattr(self, 'name', type(self).__name__)!r} does not support agentic_search"
        )

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if this runner is available and configured correctly.

        Returns:
            True if the runner's CLI binary (or env var) is present and usable,
            False otherwise. Never raises — failures surface as False.
        """
        ...

    @abstractmethod
    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        """Send prompt to the LLM and return the parsed JSON response.

        Args:
            prompt: The full prompt string to send to the LLM.
            schema: Optional JSON schema the response must conform to. Passed
                to the CLI if the vendor supports schema enforcement.

        Returns:
            Parsed dict from the LLM's JSON response.

        Raises:
            AdapterError: If the LLM call fails (non-zero exit, timeout) or the
                response body is not valid JSON.
        """
        ...
