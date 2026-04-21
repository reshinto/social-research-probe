"""LLM runner that delegates to the Google Gemini CLI."""

from __future__ import annotations

import asyncio
import json
import re
from typing import ClassVar

from social_research_probe.llm.registry import register
from social_research_probe.llm.runners.cli_json_base import AdapterError, JsonCliRunner
from social_research_probe.llm.types import AgenticSearchCitation, AgenticSearchResult
from social_research_probe.utils.subprocess_runner import run as sp_run


def _build_media_prompt(url: str, word_limit: int) -> str:
    """Compose the direct-URL summary instruction sent to Gemini."""
    return (
        f"Summarize the video at this URL in approximately {word_limit} words. "
        "Cover the main topic, key arguments or findings, target audience, and "
        "any specific claims, tools, people, or data points referenced. Be "
        "specific and factual. Do not start with 'This video' or 'In this "
        f"video'.\n\nURL: {url}"
    )


@register
class GeminiRunner(JsonCliRunner):
    """Structured JSON runner for the Gemini CLI."""

    name: ClassVar[str] = "gemini"
    binary_name: ClassVar[str] = "gemini"
    base_argv: ClassVar[tuple[str, ...]] = ("--output-format", "json")
    schema_flag: ClassVar[str | None] = None
    supports_media_url: ClassVar[bool] = True
    supports_agentic_search: ClassVar[bool] = True

    def _prompt_args(self, prompt: str) -> list[str]:
        """Gemini uses --prompt for non-interactive execution."""
        return ["--prompt", prompt]

    def _stdin_input(self, prompt: str) -> str | None:
        """Gemini prompt mode should not also receive stdin input."""
        return None

    def _parse_response(self, stdout: str) -> dict:
        """Unwrap Gemini's envelope and parse the inner JSON.

        Gemini CLI with --output-format json wraps the LLM reply in
        {"response": "<llm text>", ...}. The LLM itself may wrap its JSON
        in a markdown fence (```json ... ```). Strip both layers.
        """
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"gemini returned non-JSON envelope: {stdout[:200]!r}") from exc

        inner_text: str = envelope.get("response", "")
        # Strip optional markdown code fence.
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", inner_text.strip(), flags=re.DOTALL)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                f"gemini response field is not valid JSON: {stripped[:200]!r}"
            ) from exc

    async def summarize_media(
        self, url: str, *, word_limit: int = 100, timeout_s: float = 60.0
    ) -> str | None:
        """Ask Gemini to summarise the video at ``url`` directly.

        Returns plain prose from the envelope's ``response`` field or ``None``
        on any failure. Does not parse as JSON — the summary is natural text.
        """
        if not self.health_check():
            return None
        prompt = _build_media_prompt(url, word_limit)
        argv = [self._binary(), *self.base_argv, *self._extra_flags(), "--prompt", prompt]
        try:
            result = await asyncio.to_thread(sp_run, argv, timeout=int(timeout_s))
            envelope = json.loads(result.stdout)
        except (AdapterError, json.JSONDecodeError, OSError):
            return None
        answer = envelope.get("response", "") if isinstance(envelope, dict) else ""
        if not isinstance(answer, str):
            return None
        return answer.strip() or None

    async def agentic_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout_s: float = 60.0,
    ) -> AgenticSearchResult:
        """Run ``query`` through Gemini CLI's grounded-search mode.

        Delegates to the existing gemini_search helper in llm.gemini_cli —
        this runner owns the Gemini-specific plumbing (flag, envelope parse)
        and presents a vendor-neutral AgenticSearchResult to callers.
        """
        # Local import to avoid a circular dependency at module load time
        # (llm.gemini_cli imports from llm.base transitively via types).
        from social_research_probe.llm.gemini_cli import gemini_search

        raw = await gemini_search(query, timeout_s=timeout_s)
        citations = [
            AgenticSearchCitation(url=c.get("url", ""), title=c.get("title", ""))
            for c in raw.get("citations", [])
            if c.get("url")
        ][:max_results]
        return AgenticSearchResult(
            answer=str(raw.get("answer", "")),
            citations=citations,
            runner_name=self.name,
        )
