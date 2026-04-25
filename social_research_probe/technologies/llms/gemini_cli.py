"""LLM runner and google-search adapter for the Google Gemini CLI."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from typing import ClassVar, TypedDict

from social_research_probe.config import load_active_config
from social_research_probe.services.llm.prompts import GEMINI_MEDIA_PROMPT
from social_research_probe.services.llm.registry import register
from social_research_probe.technologies.llms import (
    AgenticSearchCitation,
    AgenticSearchResult,
    JsonCliRunner,
)
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.io.subprocess_runner import run as subprocess_run
from enum import StrEnum


class GeminiCliFlag(StrEnum):
    OUTPUT_FORMAT = "--output-format"
    PROMPT = "--prompt"
    GOOGLE_SEARCH = "--google-search"


# ---------------------------------------------------------------------------
# Gemini CLI google-search adapter (merged from llm/gemini_cli.py)
# ---------------------------------------------------------------------------

_AVAILABILITY_CACHE: bool | None = None


class Citation(TypedDict):
    """One grounding citation returned by Gemini google-search."""

    title: str
    url: str
    snippet: str


class GeminiSearchResult(TypedDict):
    """Structured payload returned by ``gemini_search``."""

    answer: str
    citations: list[Citation]


def _search_binary() -> str:
    """Return the configured Gemini CLI binary name."""
    return load_active_config().llm_settings("gemini").get("binary", "gemini")


async def gemini_cli_available() -> bool:
    """Return True iff the Gemini CLI binary is on PATH. Memoised per process."""
    global _AVAILABILITY_CACHE
    if _AVAILABILITY_CACHE is not None:
        return _AVAILABILITY_CACHE
    present = shutil.which(_search_binary()) is not None
    _AVAILABILITY_CACHE = present
    return present


def _unwrap_envelope(stdout: str) -> dict:
    """Parse Gemini's ``--output-format json`` envelope."""
    envelope = json.loads(stdout)
    if not isinstance(envelope, dict):
        raise ValueError("gemini envelope is not a JSON object")
    return envelope


def _extract_answer(envelope: dict) -> str:
    """Return the textual answer, stripping a wrapping markdown fence if any."""
    text = envelope.get("response", "")
    if not isinstance(text, str):
        return ""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)


def _extract_citations(envelope: dict) -> list[Citation]:
    """Return citation list from the envelope, tolerating schema variation."""
    raw_sources: list = []
    for key in ("grounding", "citations", "sources"):
        value = envelope.get(key)
        if isinstance(value, list):
            raw_sources = value
            break
        if isinstance(value, dict):
            nested = value.get("citations") or value.get("sources") or []
            if isinstance(nested, list):
                raw_sources = nested
                break
    out: list[Citation] = []
    for src in raw_sources:
        if not isinstance(src, dict):
            continue
        out.append(
            Citation(
                title=str(src.get("title", "") or ""),
                url=str(src.get("url", "") or src.get("link", "") or ""),
                snippet=str(src.get("snippet", "") or src.get("summary", "") or ""),
            )
        )
    return out


def _parse_search_stdout(stdout: str) -> GeminiSearchResult:
    """Parse the Gemini CLI stdout into a ``GeminiSearchResult``."""
    envelope = _unwrap_envelope(stdout)
    return GeminiSearchResult(
        answer=_extract_answer(envelope),
        citations=_extract_citations(envelope),
    )


def _run_search_sync(binary: str, query: str, timeout_s: float) -> str:
    """Invoke the Gemini CLI synchronously and return raw stdout."""
    argv = [binary, GeminiCliFlag.GOOGLE_SEARCH, GeminiCliFlag.OUTPUT_FORMAT, "json", GeminiCliFlag.PROMPT, query]
    result = subprocess_run(argv, timeout=int(timeout_s))
    return result.stdout


async def gemini_search(
    query: str,
    *,
    timeout_s: float = 30.0,
) -> GeminiSearchResult | None:
    """Run a google-search-grounded query through Gemini CLI.

    Returns None on any failure; caller treats None as "signal unavailable".
    """
    if not await gemini_cli_available():
        return None
    try:
        stdout = await asyncio.to_thread(_run_search_sync, _search_binary(), query, timeout_s)
        return _parse_search_stdout(stdout)
    except (AdapterError, json.JSONDecodeError, ValueError, OSError):
        return None


# ---------------------------------------------------------------------------
# GeminiRunner — structured JSON runner for the Gemini CLI
# ---------------------------------------------------------------------------


@register
class GeminiRunner(JsonCliRunner):
    """Structured JSON runner for the Gemini CLI."""

    name: ClassVar[str] = "gemini"
    binary_name: ClassVar[str] = "gemini"
    base_argv: ClassVar[tuple[str, ...]] = (GeminiCliFlag.OUTPUT_FORMAT, "json")
    schema_flag: ClassVar[str | None] = None
    health_check_key: ClassVar[str] = "gemini"
    enabled_config_key: ClassVar[str] = "gemini"
    supports_media_url: ClassVar[bool] = True
    supports_agentic_search: ClassVar[bool] = True

    def _prompt_args(self, prompt: str) -> list[str]:
        """Gemini uses --prompt for non-interactive execution."""
        return [GeminiCliFlag.PROMPT, prompt]

    def _stdin_input(self, prompt: str) -> str | None:
        """Gemini prompt mode should not also receive stdin input."""
        return None

    def _parse_response(self, stdout: str) -> dict:
        """Unwrap Gemini's envelope and parse the inner JSON."""
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"gemini returned non-JSON envelope: {stdout[:200]!r}") from exc

        inner_text: str = envelope.get("response", "")
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
        """Ask Gemini to summarise the video at ``url`` directly."""
        if not self.health_check():
            return None
        prompt = GEMINI_MEDIA_PROMPT.format(url=url, word_limit=word_limit)
        argv = [
            self._binary(),
            *self.base_argv,
            *self._extra_flags(),
            GeminiCliFlag.PROMPT,
            prompt,
        ]
        try:
            result = await asyncio.to_thread(subprocess_run, argv, timeout=int(timeout_s))
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
        """Run ``query`` through Gemini CLI's grounded-search mode."""
        raw = await gemini_search(query, timeout_s=timeout_s)
        citations = [
            AgenticSearchCitation(url=c.get("url", ""), title=c.get("title", ""))
            for c in (raw.get("citations", []) if raw else [])
            if c.get("url")
        ][:max_results]
        return AgenticSearchResult(
            answer=str(raw.get("answer", "") if raw else ""),
            citations=citations,
            runner_name=self.name,
        )
