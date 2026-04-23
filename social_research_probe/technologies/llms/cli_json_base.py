"""Shared JSON-over-CLI runner base for vendor LLM CLIs."""

from __future__ import annotations

import asyncio
import json
import shutil
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.errors import AdapterError
from social_research_probe.llm.base import LLMRunner
from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.types import JSONObject
from social_research_probe.utils.progress import log


class JsonCliRunner(LLMRunner, BaseTechnology[str, dict]):
    """Base class for structured JSON CLI runners.

    Inherits both LLMRunner (backward-compat sync API) and BaseTechnology
    (async API with flag checking, timing, and error isolation).
    """

    name: ClassVar[str]
    binary_name: ClassVar[str]
    base_argv: ClassVar[tuple[str, ...]]
    schema_flag: ClassVar[str | None] = "--schema"
    health_check_key: ClassVar[str] = ""
    enabled_config_key: ClassVar[str] = ""

    def _binary(self) -> str:
        """Return the configured binary, falling back to the class default."""
        return load_active_config().llm_settings(self.name).get("binary", self.binary_name)

    def _extra_flags(self) -> list[str]:
        """Return any operator-supplied extra flags for this runner."""
        return list(load_active_config().llm_settings(self.name).get("extra_flags", []))

    def health_check(self) -> bool:
        """Return True if the configured binary is available on PATH."""
        return shutil.which(self._binary()) is not None

    def _build_argv(self, schema: JSONObject | None) -> list[str]:
        """Build the argv list for the configured CLI invocation."""
        argv = [self._binary(), *self.base_argv, *self._extra_flags()]
        if schema and self.schema_flag:
            argv += [self.schema_flag, json.dumps(schema)]
        return argv

    def _prompt_args(self, prompt: str) -> list[str]:
        """Return argv fragments that carry the prompt for this CLI."""
        return []

    def _stdin_input(self, prompt: str) -> str | None:
        """Return stdin payload for this CLI."""
        return prompt

    def _parse_response(self, stdout: str) -> dict:
        """Parse the JSON stdout emitted by the CLI."""
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"{self.name} returned non-JSON: {stdout[:200]!r}") from exc

    def run(self, prompt: str, *, schema: JSONObject | None = None) -> dict:
        """Send prompt to the CLI and return its parsed JSON response (sync)."""
        from social_research_probe.utils.subprocess_runner import run as sp_run

        log(f"[srp] LLM ({self.name}): running structured JSON task")
        timeout = load_active_config().llm_timeout_seconds
        result = sp_run(
            [*self._build_argv(schema), *self._prompt_args(prompt)],
            input=self._stdin_input(prompt),
            timeout=timeout,
        )
        return self._parse_response(result.stdout)

    async def _execute(self, data: str) -> dict:
        """Async wrapper around run() for BaseTechnology.execute() compatibility."""
        return await asyncio.to_thread(self.run, data)
