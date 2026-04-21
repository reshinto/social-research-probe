"""Gemini CLI google-search adapter.

Direct, Gemini-specific adapter — not a generalised runner abstraction. Used
only by the corroboration layer for fact-check queries. Fails silent (returns
``None``) when the Gemini CLI is missing, times out, or produces malformed
output, so callers can degrade gracefully.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from typing import TypedDict

from social_research_probe.config import load_active_config
from social_research_probe.errors import AdapterError
from social_research_probe.utils.subprocess_runner import run as sp_run

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


def _binary() -> str:
    """Return the configured Gemini CLI binary name."""
    return load_active_config().llm_settings("gemini").get("binary", "gemini")


async def gemini_cli_available() -> bool:
    """Return True iff the Gemini CLI binary is on PATH. Memoised per process."""
    global _AVAILABILITY_CACHE
    if _AVAILABILITY_CACHE is not None:
        return _AVAILABILITY_CACHE
    present = shutil.which(_binary()) is not None
    _AVAILABILITY_CACHE = present
    return present


def _unwrap_envelope(stdout: str) -> dict:
    """Parse Gemini's ``--output-format json`` envelope (response may be fenced)."""
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
    argv = [binary, "--google-search", "--output-format", "json", "--prompt", query]
    result = sp_run(argv, timeout=int(timeout_s))
    return result.stdout


async def gemini_search(
    query: str,
    *,
    timeout_s: float = 30.0,
) -> GeminiSearchResult | None:
    """Run a google-search-grounded query through Gemini CLI.

    Returns ``None`` on any failure (missing CLI, timeout, parse error). The
    caller is expected to treat ``None`` as "signal unavailable" and continue.
    """
    if not await gemini_cli_available():
        return None
    try:
        stdout = await asyncio.to_thread(_run_search_sync, _binary(), query, timeout_s)
        return _parse_search_stdout(stdout)
    except (AdapterError, json.JSONDecodeError, ValueError, OSError):
        return None
