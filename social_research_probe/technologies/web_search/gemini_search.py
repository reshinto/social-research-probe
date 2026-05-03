"""Gemini CLI agentic web search technology."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies.llms import AgenticSearchResult
from social_research_probe.technologies.llms.gemini_cli import GeminiRunner


class GeminiWebSearch(GeminiRunner):
    """Agentic web search via Gemini CLI google-search grounding.

    Extends GeminiRunner; shares health_check_key with GeminiRunner so the binary is health-
    checked only once per run.

    Examples:
        Input:
            GeminiWebSearch
        Output:
            GeminiWebSearch
    """

    name: ClassVar[str] = "gemini_web_search"
    health_check_key: ClassVar[str] = "gemini"
    enabled_config_key: ClassVar[str] = "gemini"

    async def _execute(self, data: str) -> AgenticSearchResult:
        """Run this component and return the project-shaped output expected by its service.

        The helper keeps a small project rule named and documented at the boundary where it is used.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            AgenticSearchResult with the answer text, citations, and runner name.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                AgenticSearchResult(answer="Supported by two sources.", citations=[], runner_name="codex")
        """
        return await self.agentic_search(data)
