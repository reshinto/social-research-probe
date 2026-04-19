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
    base_argv: ClassVar[tuple[str, ...]] = ("--output-format", "json")
