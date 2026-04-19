"""LLM runner that delegates to the Google Gemini CLI."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.llm.registry import register
from social_research_probe.llm.runners.cli_json_base import JsonCliRunner


@register
class GeminiRunner(JsonCliRunner):
    """Structured JSON runner for the Gemini CLI."""

    name: ClassVar[str] = "gemini"
    binary_name: ClassVar[str] = "gemini"
    base_argv: ClassVar[tuple[str, ...]] = ("--output-format", "json")
    schema_flag: ClassVar[str | None] = None

    def _prompt_args(self, prompt: str) -> list[str]:
        """Gemini uses --prompt for non-interactive execution."""
        return ["--prompt", prompt]

    def _stdin_input(self, prompt: str) -> str | None:
        """Gemini prompt mode should not also receive stdin input."""
        return None
