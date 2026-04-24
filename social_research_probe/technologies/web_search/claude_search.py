"""Claude CLI agentic web search technology."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies.llms.claude_cli import ClaudeRunner
from social_research_probe.technologies.llms import AgenticSearchResult


class ClaudeWebSearch(ClaudeRunner):
    """Agentic web search via Claude CLI with the web_search tool.

    Extends ClaudeRunner; shares health_check_key with ClaudeRunner.
    """

    name: ClassVar[str] = "claude_web_search"
    health_check_key: ClassVar[str] = "claude"
    enabled_config_key: ClassVar[str] = "claude"

    async def _execute(self, data: str) -> AgenticSearchResult:
        """Run an agentic Claude web search for the given query string."""
        return await self.agentic_search(data)
