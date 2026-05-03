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
from social_research_probe.utils.llm import ensemble, registry, schemas

# ---------------------------------------------------------------------------
# Exception for capability checks
# ---------------------------------------------------------------------------


class CapabilityUnavailableError(RuntimeError):
    """Raised when a caller invokes a capability the active runner doesn't support.

    Example: calling ``agentic_search`` on a runner whose ``supports_agentic_search`` is

    False.

    Examples:
        Input:
            CapabilityUnavailableError
        Output:
            CapabilityUnavailableError
    """


# ---------------------------------------------------------------------------
# Abstract base class for all LLM runners
# ---------------------------------------------------------------------------


class LLMRunner(ABC):
    """Contract that every LLM runner must fulfil.

    Purpose: provide a uniform interface so callers are decoupled from any specific LLM
    vendor or binary.

    Lifecycle: subclasses are registered at import time via the @register decorator in
    llm.registry; the registry instantiates them on demand.

    Who instantiates it: llm.registry.get_runner(), never called directly.

    ABC/protocol fulfilled: ABC with two abstract methods — health_check and run.

    Examples:
        Input:
            LLMRunner
        Output:
            LLMRunner
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

        ``supports_media_url`` to True. Callers treat ``None`` as "signal unavailable"
        and continue. Must never raise.

        Args:
            url: Stable source identifier or URL used to join records across stages and exports.
            word_limit: Count, database id, index, or limit that bounds the work being performed.
            timeout_s: Numeric score, threshold, prior, or confidence value.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                await summarize_media(
                    url="https://youtu.be/abc123",
                    word_limit=3,
                    timeout_s=0.75,
                )
            Output:
                "AI safety"
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

        Runners that support it (flip ``supports_agentic_search`` to True) use their
        vendor-native capability: Gemini's google-search grounding, Claude's

        ``web_search`` tool, Codex's ``--search`` flag. Runners that don't support it
        must leave ``supports_agentic_search`` False; calling this method on them raises

        :class:`CapabilityUnavailableError` so mis-routed callers fail loudly instead of
        silently returning no evidence.

        Args:
            query: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                   to a provider.
            max_results: Count, database id, index, or limit that bounds the work being performed.
            timeout_s: Numeric score, threshold, prior, or confidence value.

        Returns:
            AgenticSearchResult with the answer text, citations, and runner name.

        Raises:
                                            CapabilityUnavailableError: If the runner does not support agentic
                                                search.
                                            AdapterError: If the vendor call fails at runtime.




        Examples:
            Input:
                await agentic_search(
                    query="AI safety benchmarks",
                    max_results=3,
                    timeout_s=0.75,
                )
            Output:
                AgenticSearchResult(answer="Supported by two sources.", citations=[], runner_name="codex")
        """
        raise CapabilityUnavailableError(
            f"runner {getattr(self, 'name', type(self).__name__)!r} does not support agentic_search"
        )

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if this runner is available and configured correctly.

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
    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        """Send prompt to the LLM and return the parsed JSON response.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                    to a provider.
            schema: JSON schema that the LLM or validator must satisfy.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Raises:
                                            AdapterError: If the LLM call fails (non-zero exit, timeout) or the
                                                response body is not valid JSON.




        Examples:
            Input:
                run(
                    prompt="Summarize this source.",
                    schema={"enabled": True},
                )
            Output:
                {"enabled": True}
        """
        ...


# ---------------------------------------------------------------------------
# Structured JSON CLI runner base class
# ---------------------------------------------------------------------------


class JsonCliRunner(LLMRunner, BaseTechnology[str, dict]):
    """Base class for structured JSON CLI runners.

    Inherits both LLMRunner (backward-compat sync API) and BaseTechnology (async API with
    flag checking, timing, and error isolation).

    Examples:
        Input:
            JsonCliRunner
        Output:
            JsonCliRunner
    """

    name: ClassVar[str]
    binary_name: ClassVar[str]
    base_argv: ClassVar[tuple[str, ...]]
    schema_flag: ClassVar[str | None] = "--schema"
    health_check_key: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""

    def _binary(self) -> str:
        """Return the configured binary, falling back to the class default.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Returns:
            Normalized string used as a config key, provider value, or report field.

        Examples:
            Input:
                _binary()
            Output:
                "AI safety"
        """
        return load_active_config().llm_settings(self.name).get("binary", self.binary_name)

    def _extra_flags(self) -> list[str]:
        """Return any operator-supplied extra flags for this runner.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _extra_flags()
            Output:
                ["AI safety", "model evaluation"]
        """
        return list(load_active_config().llm_settings(self.name).get("extra_flags", []))

    def health_check(self) -> bool:
        """Return True if the configured binary is available on PATH.

        Returns:
            True when the condition is satisfied; otherwise False.

        Examples:
            Input:
                health_check()
            Output:
                True
        """
        return shutil.which(self._binary()) is not None

    def _build_argv(self, schema: JSONObject | None) -> list[str]:
        """Build the argv list for the configured CLI invocation.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            schema: JSON schema that the LLM or validator must satisfy.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _build_argv(
                    schema="AI safety",
                )
            Output:
                ["AI safety", "model evaluation"]
        """
        argv = [self._binary(), *self.base_argv, *self._extra_flags()]
        if schema and self.schema_flag:
            argv += [self.schema_flag, json.dumps(schema)]
        return argv

    def _prompt_args(self, prompt: str) -> list[str]:
        """Return argv fragments that carry the prompt for this CLI.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                    to a provider.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                _prompt_args(
                    prompt="Summarize this source.",
                )
            Output:
                ["AI safety", "model evaluation"]
        """
        return []

    def _stdin_input(self, prompt: str) -> str | None:
        """Return stdin payload for this CLI.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                    to a provider.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                _stdin_input(
                    prompt="Summarize this source.",
                )
            Output:
                "AI safety"
        """
        return prompt

    def _parse_response(self, stdout: str) -> dict:
        """Parse the JSON stdout emitted by the CLI.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            stdout: Captured standard output from the runner process.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                _parse_response(
                    stdout="AI safety",
                )
            Output:
                {"enabled": True}
        """
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"{self.name} returned non-JSON: {stdout[:200]!r}") from exc

    def run(self, prompt: str, *, schema: JSONObject | None = None) -> dict:
        """Send prompt to the CLI and return its parsed JSON response (sync).

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                    to a provider.
            schema: JSON schema that the LLM or validator must satisfy.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                run(
                    prompt="Summarize this source.",
                    schema="AI safety",
                )
            Output:
                {"enabled": True}
        """
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
        """Async wrapper around run() for BaseTechnology.execute() compatibility.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                {"enabled": True}
        """
        return await asyncio.to_thread(self.run, data)


class LLMTech(BaseTechnology[str, dict]):
    """Technology adapter wrapping one registered LLM runner for structured JSON calls.

    Examples:
        Input:
            LLMTech
        Output:
            LLMTech
    """

    enabled_config_key: ClassVar[str] = ""

    def __init__(self, runner_name: str, schema: dict | None = None) -> None:
        """Store constructor options used by later method calls.

        LLM helpers hide runner-specific process and schema handling behind one project-level contract.

        Args:
            runner_name: Provider or runner selected for this operation.
            schema: JSON schema that the LLM or validator must satisfy.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                __init__(
                    runner_name="codex",
                    schema={"enabled": True},
                )
            Output:
                None
        """
        super().__init__()
        self._runner_name = runner_name
        self._schema = schema

    @property
    def name(self) -> str:  # type: ignore[override]
        """Document the name rule at the boundary where callers use it.

        LLM helpers isolate prompt, process, and schema handling so services can request structured
        results without knowing the runner details.

        Returns:
            The configured name setting.

        Examples:
            Input:
                stage.name
            Output:
                "AI safety"
        """
        return f"llm.{self._runner_name}"

    async def _execute(self, prompt: str) -> dict | None:
        """Return the execute.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            prompt: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
                    to a provider.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    prompt="Summarize this source.",
                )
            Output:
                {"enabled": True}
        """
        from social_research_probe.utils.llm.registry import get_runner

        runner = get_runner(self._runner_name)
        if not runner.health_check():
            return None
        return await asyncio.to_thread(runner.run, prompt, schema=self._schema)


# ---------------------------------------------------------------------------
# Data structures for search results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgenticSearchCitation:
    """One citation returned by a runner's agentic search.

    Examples:
        Input:
            AgenticSearchCitation
        Output:
            AgenticSearchCitation(url="https://example.com", title="Example")
    """

    url: str
    title: str = ""


@dataclass
class AgenticSearchResult:
    """Structured payload returned by every runner's ``agentic_search``.

    Runner implementations wrap their native search feature (Gemini google-search, Claude
    web_search tool, Codex ``--search``) so callers can treat them uniformly. The shape is
    intentionally narrow — enough for corroboration providers to apply source-quality
    filtering and compute a verdict.

    Examples:
        Input:
            AgenticSearchResult
        Output:
            AgenticSearchResult(answer="Supported by two sources.", citations=[], runner_name="codex")
    """

    answer: str
    citations: list[AgenticSearchCitation] = field(default_factory=list)
    runner_name: str = ""


__all__ = [
    "AgenticSearchCitation",
    "AgenticSearchResult",
    "CapabilityUnavailableError",
    "JsonCliRunner",
    "LLMRunner",
    "LLMTech",
    "ensemble",
    "registry",
    "schemas",
]
