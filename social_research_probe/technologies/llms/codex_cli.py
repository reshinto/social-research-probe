"""LLM runner that delegates to the OpenAI Codex CLI."""

from __future__ import annotations

import asyncio
import json
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.services.llm.prompts import CODEX_SEARCH_PROMPT
from social_research_probe.services.llm.registry import register
from social_research_probe.technologies.llms import (
    AgenticSearchCitation,
    AgenticSearchResult,
    JsonCliRunner,
)
from social_research_probe.utils.core.errors import AdapterError
from social_research_probe.utils.core.types import JSONObject


class CodexCliFlag(StrEnum):
    OUTPUT_LAST_MESSAGE = "--output-last-message"
    OUTPUT_SCHEMA = "--output-schema"
    SEARCH = "--search"


@register
class CodexRunner(JsonCliRunner):
    """Structured JSON runner for the Codex CLI."""

    name: ClassVar[str] = "codex"
    binary_name: ClassVar[str] = "codex"
    base_argv: ClassVar[tuple[str, ...]] = ("exec",)
    schema_flag: ClassVar[str | None] = None
    health_check_key: ClassVar[str] = "codex"
    enabled_config_key: ClassVar[str] = "codex"
    supports_agentic_search: ClassVar[bool] = True

    def run(self, prompt: str, *, schema: JSONObject | None = None) -> dict:
        """Send prompt to Codex exec and parse the final message as JSON."""
        from social_research_probe.utils.io.subprocess_runner import run as sp_run

        timeout = load_active_config().llm_timeout_seconds
        with TemporaryDirectory(prefix="srp-codex-") as tmpdir:
            tmp = Path(tmpdir)
            output_path = tmp / "last-message.json"
            argv = [*self._build_argv(None), CodexCliFlag.OUTPUT_LAST_MESSAGE, str(output_path)]
            if schema:
                schema_path = tmp / "schema.json"
                schema_path.write_text(json.dumps(schema), encoding="utf-8")
                argv += [CodexCliFlag.OUTPUT_SCHEMA, str(schema_path)]
            result = sp_run([*argv, prompt], input=None, timeout=timeout)
            text = (
                output_path.read_text(encoding="utf-8") if output_path.exists() else result.stdout
            )
        try:
            return self._parse_response(text)
        except AdapterError as exc:
            raise AdapterError(f"codex returned non-JSON final message: {text[:200]!r}") from exc

    async def agentic_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout_s: float = 60.0,
    ) -> AgenticSearchResult:
        """Run ``query`` via Codex CLI with its ``--search`` flag."""
        from social_research_probe.utils.io.subprocess_runner import run as sp_run

        prompt = CODEX_SEARCH_PROMPT.format(query=query)
        with TemporaryDirectory(prefix="srp-codex-search-") as tmpdir:
            output_path = Path(tmpdir) / "last-message.json"
            argv = [
                *self._build_argv(None),
                CodexCliFlag.SEARCH,
                CodexCliFlag.OUTPUT_LAST_MESSAGE,
                str(output_path),
                prompt,
            ]
            try:
                result = await asyncio.to_thread(sp_run, argv, input=None, timeout=int(timeout_s))
                text = (
                    output_path.read_text(encoding="utf-8")
                    if output_path.exists()
                    else result.stdout
                )
                payload = json.loads(text)
            except (AdapterError, json.JSONDecodeError, OSError) as exc:
                raise AdapterError(f"codex agentic_search failed: {exc}") from exc

        answer = str(payload.get("answer", "")) if isinstance(payload, dict) else ""
        raw_citations = payload.get("citations", []) if isinstance(payload, dict) else []
        citations = [
            AgenticSearchCitation(url=str(c.get("url", "")), title=str(c.get("title", "")))
            for c in raw_citations
            if isinstance(c, dict) and c.get("url")
        ][:max_results]
        return AgenticSearchResult(answer=answer, citations=citations, runner_name=self.name)
