"""LLM runner that delegates to the Anthropic Claude CLI."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.llm.registry import register
from social_research_probe.llm.runners.cli_json_base import JsonCliRunner


@register
class ClaudeRunner(JsonCliRunner):
    """Structured JSON runner for the Claude CLI."""

    name: ClassVar[str] = "claude"
    binary_name: ClassVar[str] = "claude"
    base_argv: ClassVar[tuple[str, ...]] = ("--print", "--output-format", "json")
    schema_flag: ClassVar[str | None] = "--json-schema"

    def _prompt_args(self, prompt: str) -> list[str]:
        """Claude expects the prompt as a positional arg in print mode."""
        return [prompt]

    def _stdin_input(self, prompt: str) -> str | None:
        """Claude print mode should not wait on stdin."""
        return None
