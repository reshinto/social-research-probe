"""LLM runner that delegates to the OpenAI Codex CLI."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.errors import AdapterError
from social_research_probe.llm.registry import register
from social_research_probe.llm.runners.cli_json_base import JsonCliRunner
from social_research_probe.types import JSONObject
from social_research_probe.utils.progress import log


@register
class CodexRunner(JsonCliRunner):
    """Structured JSON runner for the Codex CLI."""

    name: ClassVar[str] = "codex"
    binary_name: ClassVar[str] = "codex"
    base_argv: ClassVar[tuple[str, ...]] = ("exec",)
    schema_flag: ClassVar[str | None] = None

    def run(self, prompt: str, *, schema: JSONObject | None = None) -> dict:
        """Send prompt to Codex exec and parse the final message as JSON."""
        from social_research_probe.utils.subprocess_runner import run as sp_run

        log(f"[srp] CodexRunner LLM ({self.name}): running structured JSON task")
        timeout = load_active_config().llm_timeout_seconds
        with TemporaryDirectory(prefix="srp-codex-") as tmpdir:
            tmp = Path(tmpdir)
            output_path = tmp / "last-message.json"
            argv = [*self._build_argv(None), "--output-last-message", str(output_path)]
            if schema:
                schema_path = tmp / "schema.json"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                argv += ["--output-schema", str(schema_path)]
            result = sp_run([*argv, prompt], input=None, timeout=timeout)
            text = (
                output_path.read_text(encoding="utf-8") if output_path.exists() else result.stdout
            )
        try:
            return self._parse_response(text)
        except AdapterError as exc:
            raise AdapterError(f"codex returned non-JSON final message: {text[:200]!r}") from exc
