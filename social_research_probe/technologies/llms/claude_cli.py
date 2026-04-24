"""LLM runner that delegates to the Anthropic Claude CLI."""

from __future__ import annotations

import asyncio
import json
import re
from typing import ClassVar

from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.technologies.llms.registry import register
from social_research_probe.technologies.llms.types import AgenticSearchCitation, AgenticSearchResult
from social_research_probe.technologies.llms.cli_json_base import JsonCliRunner
from social_research_probe.utils.io.subprocess_runner import run as sp_run

_URL_RE = re.compile(r"https?://[^\s)\]]+")


def _build_search_prompt(query: str) -> str:
    """Compose the prompt that instructs Claude to use its web_search tool."""
    return (
        "Use the web_search tool to find authoritative sources about the "
        "following claim. Then reply with a single JSON object "
        '{"answer": "...", "citations": [{"url": "...", "title": "..."}]}. '
        "Do not include citations for video hosts (youtube.com, vimeo.com, "
        "tiktok.com) — they cannot be verified from snippets.\n\n"
        f"Claim: {query}"
    )


def _parse_claude_search_body(
    body: str,
) -> tuple[str, list[AgenticSearchCitation]]:
    """Extract ``answer`` + citations from Claude's reply body.

    Primary path: body contains ``{"answer": ..., "citations": [...]}``.
    Fallback: extract bare URLs from free text when the JSON block is missing.
    """
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", body.strip(), flags=re.DOTALL)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        answer = str(payload.get("answer", ""))
        raw_citations = payload.get("citations", [])
        citations = [
            AgenticSearchCitation(url=str(c.get("url", "")), title=str(c.get("title", "")))
            for c in raw_citations
            if isinstance(c, dict) and c.get("url")
        ]
        return answer, citations
    urls = _URL_RE.findall(body)
    fallback_citations = [AgenticSearchCitation(url=url) for url in urls]
    return body.strip(), fallback_citations


@register
class ClaudeRunner(JsonCliRunner):
    """Structured JSON runner for the Claude CLI."""

    name: ClassVar[str] = "claude"
    binary_name: ClassVar[str] = "claude"
    base_argv: ClassVar[tuple[str, ...]] = ("--print", "--output-format", "json")
    schema_flag: ClassVar[str | None] = "--json-schema"
    health_check_key: ClassVar[str] = "claude"
    enabled_config_key: ClassVar[str] = "claude"
    supports_agentic_search: ClassVar[bool] = True

    def _prompt_args(self, prompt: str) -> list[str]:
        """Claude expects the prompt as a positional arg in print mode."""
        return [prompt]

    def _stdin_input(self, prompt: str) -> str | None:
        """Claude print mode should not wait on stdin."""
        return None

    async def agentic_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout_s: float = 60.0,
    ) -> AgenticSearchResult:
        """Run ``query`` via Claude CLI with the ``web_search`` tool enabled."""
        prompt = _build_search_prompt(query)
        argv = [
            self._binary(),
            *self.base_argv,
            *self._extra_flags(),
            "--allowed-tools",
            "web_search",
            prompt,
        ]
        try:
            result = await asyncio.to_thread(sp_run, argv, timeout=int(timeout_s))
            envelope = json.loads(result.stdout)
        except (AdapterError, json.JSONDecodeError, OSError) as exc:
            raise AdapterError(f"claude agentic_search failed: {exc}") from exc

        inner = envelope.get("result", "") if isinstance(envelope, dict) else ""
        if not isinstance(inner, str):
            inner = ""
        answer, citations = _parse_claude_search_body(inner)
        return AgenticSearchResult(
            answer=answer,
            citations=citations[:max_results],
            runner_name=self.name,
        )
