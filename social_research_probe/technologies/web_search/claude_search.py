"""Claude CLI agentic web search technology."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.technologies.llms import AgenticSearchResult
from social_research_probe.technologies.llms.claude_cli import ClaudeRunner


class ClaudeWebSearch(ClaudeRunner):
    """Agentic web search via Claude CLI with the web_search tool.

    Extends ClaudeRunner; shares health_check_key with ClaudeRunner.

    Examples:
        Input:
            ClaudeWebSearch
        Output:
            ClaudeWebSearch
    """

    name: ClassVar[str] = "claude_web_search"
    health_check_key: ClassVar[str] = "claude"
    enabled_config_key: ClassVar[str] = "claude"

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
