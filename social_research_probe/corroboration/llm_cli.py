"""LLM-based corroboration backend — fallback when no web search API is available.

What: Implements CorroborationBackend using a registered LLM runner (e.g. the
Claude CLI runner) to evaluate a claim against its own source text.

Why: Provides a zero-key-required fallback so corroboration always has at least
one backend available, even in offline or restricted environments.

Who calls it: corroboration/host.py via the registry; registered automatically
at import time when the corroboration package is loaded.
"""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.registry import register


@register
class LLMCliBackend(CorroborationBackend):
    """Corroboration backend that uses a registered LLM runner CLI.

    Purpose: Asks the configured LLM to evaluate a claim against the claim's
    own source_text. It is a last resort — less reliable than a web search API
    but requires no external API key.

    Lifecycle: Instantiated by get_backend("llm_cli"); runner_name defaults to
    "claude" but can be overridden for testing.

    ABC contract: implements health_check() and corroborate().
    """

    name: ClassVar[str] = "llm_cli"

    def __init__(self, runner_name: str = "claude") -> None:
        """Initialise the backend with the name of an LLM runner.

        Args:
            runner_name: Key used to look up the runner in the LLM registry.
                Defaults to "claude". Override in tests to inject a stub.
        """
        self._runner_name = runner_name

    def health_check(self) -> bool:
        """Return True if the configured LLM runner passes its own health check.

        Delegates entirely to the underlying runner's health_check() method so
        this backend reports exactly the same availability as the LLM runner.

        Returns:
            True when the runner is reachable and configured; False otherwise.
        """
        from social_research_probe.llm.registry import get_runner

        try:
            runner = get_runner(self._runner_name)
            return runner.health_check()
        except Exception:
            # Any registry or runner error means the backend is unavailable.
            return False

    def _build_prompt(self, claim) -> str:
        """Build the corroboration prompt for this claim.

        Kept as a standalone method so callers can unit-test prompt construction
        without invoking the LLM subprocess.

        Args:
            claim: A Claim dataclass instance. Uses claim.text and
                claim.source_text.

        Returns:
            Formatted prompt string ready to send to the LLM runner.
        """
        from social_research_probe.llm.prompts import CORROBORATION_PROMPT

        return CORROBORATION_PROMPT.format(
            claim=claim.text,
            sources=claim.source_text or "(no source text available)",
        )

    def _parse_result(self, raw: dict, claim) -> CorroborationResult:
        """Extract a CorroborationResult from the LLM's JSON response.

        Validates the verdict against the allowed values and falls back to
        'inconclusive' for anything unexpected, making the backend robust to
        hallucinated or malformed LLM output.

        Args:
            raw: Dict returned by the LLM runner (parsed JSON).
            claim: Original Claim — not used directly but kept in the signature
                for consistency with other backends that need claim metadata.

        Returns:
            A CorroborationResult with verdict, confidence, and reasoning
            populated from ``raw``.
        """
        verdict = raw.get("verdict", "inconclusive")
        # Guard against the LLM returning an unrecognised verdict label.
        if verdict not in ("supported", "refuted", "inconclusive"):
            verdict = "inconclusive"
        return CorroborationResult(
            verdict=verdict,
            confidence=float(raw.get("confidence", 0.5)),
            reasoning=raw.get("reasoning", ""),
            backend_name=self.name,
        )

    def corroborate(self, claim) -> CorroborationResult:
        """Send the claim to the LLM runner and parse the corroboration verdict.

        Args:
            claim: A Claim dataclass instance to corroborate.

        Returns:
            CorroborationResult parsed from the LLM's JSON response.

        Raises:
            AdapterError: if the LLM runner raises or returns an unparseable
                response.
        """
        from social_research_probe.llm.registry import get_runner

        runner = get_runner(self._runner_name)
        prompt = self._build_prompt(claim)
        raw = runner.run(
            prompt,
            schema={
                "type": "object",
                "properties": {
                    "verdict": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
            },
        )
        return self._parse_result(raw, claim)
