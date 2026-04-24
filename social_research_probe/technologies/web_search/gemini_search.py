"""Gemini CLI agentic web search technology."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies.llms.gemini_cli import GeminiRunner
from social_research_probe.technologies.llms.types import AgenticSearchResult


class GeminiWebSearch(GeminiRunner):
    """Agentic web search via Gemini CLI google-search grounding.

    Extends GeminiRunner; shares health_check_key with GeminiRunner so the
    binary is health-checked only once per run.
    """

    name: ClassVar[str] = "gemini_web_search"
    health_check_key: ClassVar[str] = "gemini"
    enabled_config_key: ClassVar[str] = "gemini"

    async def _execute(self, data: str) -> AgenticSearchResult:
        """Run a grounded Gemini google-search for the given query string."""
        return await self.agentic_search(data)
