"""LLM runner that delegates to the Google Gemini CLI."""

from __future__ import annotations

import json
import re
from typing import ClassVar

from social_research_probe.llm.registry import register
from social_research_probe.llm.runners.cli_json_base import AdapterError, JsonCliRunner


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

    def _parse_response(self, stdout: str) -> dict:
        """Unwrap Gemini's envelope and parse the inner JSON.

        Gemini CLI with --output-format json wraps the LLM reply in
        {"response": "<llm text>", ...}. The LLM itself may wrap its JSON
        in a markdown fence (```json ... ```). Strip both layers.
        """
        try:
            envelope = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"gemini returned non-JSON envelope: {stdout[:200]!r}") from exc

        inner_text: str = envelope.get("response", "")
        # Strip optional markdown code fence.
        stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", inner_text.strip(), flags=re.DOTALL)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                f"gemini response field is not valid JSON: {stripped[:200]!r}"
            ) from exc
