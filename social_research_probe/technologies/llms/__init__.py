"""LLM technology adapters — registers all available runners on import."""

from __future__ import annotations

import asyncio
import json
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.core.types import JSONObject
from social_research_probe.utils.display.progress import log

# ---------------------------------------------------------------------------
# Exception for capability checks
# ---------------------------------------------------------------------------


class CapabilityUnavailableError(RuntimeError):
    """Raised when a caller invokes a capability the active runner doesn't support.

    Example: calling ``agentic_search`` on a runner whose
    ``supports_agentic_search`` is False.
    """


# ---------------------------------------------------------------------------
# Abstract base class for all LLM runners
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Structured JSON CLI runner base class
# ---------------------------------------------------------------------------


class JsonCliRunner(LLMRunner, BaseTechnology[str, dict]):
    """Base class for structured JSON CLI runners.

    Inherits both LLMRunner (backward-compat sync API) and BaseTechnology
    (async API with flag checking, timing, and error isolation).
    """

    name: ClassVar[str]
    binary_name: ClassVar[str]
    base_argv: ClassVar[tuple[str, ...]]
    schema_flag: ClassVar[str | None] = "--schema"
    health_check_key: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""

    def _binary(self) -> str:
        """Return the configured binary, falling back to the class default."""
        return load_active_config().llm_settings(self.name).get("binary", self.binary_name)

    def _extra_flags(self) -> list[str]:
        """Return any operator-supplied extra flags for this runner."""
        return list(load_active_config().llm_settings(self.name).get("extra_flags", []))

    def health_check(self) -> bool:
        """Return True if the configured binary is available on PATH."""
        return shutil.which(self._binary()) is not None

    def _build_argv(self, schema: JSONObject | None) -> list[str]:
        """Build the argv list for the configured CLI invocation."""
        argv = [self._binary(), *self.base_argv, *self._extra_flags()]
        if schema and self.schema_flag:
            argv += [self.schema_flag, json.dumps(schema)]
        return argv

    def _prompt_args(self, prompt: str) -> list[str]:
        """Return argv fragments that carry the prompt for this CLI."""
        return []

    def _stdin_input(self, prompt: str) -> str | None:
        """Return stdin payload for this CLI."""
        return prompt

    def _parse_response(self, stdout: str) -> dict:
        """Parse the JSON stdout emitted by the CLI."""
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"{self.name} returned non-JSON: {stdout[:200]!r}") from exc

    def run(self, prompt: str, *, schema: JSONObject | None = None) -> dict:
        """Send prompt to the CLI and return its parsed JSON response (sync)."""
        from social_research_probe.utils.io.subprocess_runner import run as sp_run

        log(f"[srp] LLM ({self.name}): running structured JSON task")
        timeout = load_active_config().llm_timeout_seconds
        result = sp_run(
            [*self._build_argv(schema), *self._prompt_args(prompt)],
            input=self._stdin_input(prompt),
            timeout=timeout,
        )
        return self._parse_response(result.stdout)

    async def _execute(self, data: str) -> dict:
        """Async wrapper around run() for BaseTechnology.execute() compatibility."""
        return await asyncio.to_thread(self.run, data)


# ---------------------------------------------------------------------------
# Data structures for search results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgenticSearchCitation:
    """One citation returned by a runner's agentic search.

    Attributes:
        url: Absolute URL of the cited source. Empty string when the runner
            returned a citation without a URL (rare; caller should drop these).
        title: Human-readable title of the cited source, or empty string when
            the runner did not provide one.
    """

    url: str
    title: str = ""


@dataclass
class AgenticSearchResult:
    """Structured payload returned by every runner's ``agentic_search``.

    Runner implementations wrap their native search feature (Gemini google-search,
    Claude web_search tool, Codex ``--search``) so callers can treat them
    uniformly. The shape is intentionally narrow — enough for corroboration
    providers to apply source-quality filtering and compute a verdict.

    Attributes:
        answer: Natural-language answer synthesised by the runner.
        citations: Source URLs cited in the answer. May be empty if the runner
            produced an answer without citations; caller decides how to treat.
        runner_name: Identifier of the runner that produced the result
            (``"gemini"``, ``"claude"``, ``"codex"``). Useful for debugging and
            for logging which runner actually ran.
    """

    answer: str
    citations: list[AgenticSearchCitation] = field(default_factory=list)
    runner_name: str = ""
