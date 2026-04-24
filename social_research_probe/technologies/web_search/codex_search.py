"""Codex CLI agentic web search technology."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies.llms import AgenticSearchResult
from social_research_probe.technologies.llms.codex_cli import CodexRunner


class CodexWebSearch(CodexRunner):
    """Agentic web search via Codex CLI with the --search flag.

    Extends CodexRunner; shares health_check_key with CodexRunner.
    """

    name: ClassVar[str] = "codex_web_search"
    health_check_key: ClassVar[str] = "codex"
    enabled_config_key: ClassVar[str] = "codex"

    async def _execute(self, data: str) -> AgenticSearchResult:
        """Run an agentic Codex web search for the given query string."""
        return await self.agentic_search(data)
