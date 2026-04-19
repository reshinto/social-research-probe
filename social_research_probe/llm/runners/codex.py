"""LLM runner that delegates to the OpenAI Codex CLI."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.llm.registry import register
from social_research_probe.llm.runners.cli_json_base import JsonCliRunner


@register
class CodexRunner(JsonCliRunner):
    """Structured JSON runner for the Codex CLI."""

    name: ClassVar[str] = "codex"
    binary_name: ClassVar[str] = "codex"
    base_argv: ClassVar[tuple[str, ...]] = ("--json",)
