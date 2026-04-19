"""Shared JSON-over-CLI runner logic for vendor CLIs.

Claude, Gemini, and Codex all follow the same broad shape in this project:
check a binary on PATH, optionally append ``--schema`` with a JSON-encoded
schema, run a subprocess, then parse JSON stdout. This base class keeps that
behaviour in one place so the vendor modules only declare their identity and
base argv.
"""

from __future__ import annotations

import json
import shutil
from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.errors import AdapterError
from social_research_probe.llm.base import LLMRunner
from social_research_probe.types import JSONObject
from social_research_probe.utils.progress import log


class JsonCliRunner(LLMRunner):
    """Base class for structured JSON CLI runners."""

    name: ClassVar[str]
    binary_name: ClassVar[str]
    base_argv: ClassVar[tuple[str, ...]]

    def _binary(self) -> str:
        """Return the configured binary for this runner, falling back to the default."""
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
        if schema:
            argv += ["--schema", json.dumps(schema)]
        return argv

    def _parse_response(self, stdout: str) -> dict:
        """Parse the JSON stdout emitted by the CLI."""
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"{self.name} returned non-JSON: {stdout[:200]!r}") from exc

    def run(self, prompt: str, *, schema: JSONObject | None = None) -> dict:
        """Send prompt to the CLI and return its parsed JSON response."""
        from social_research_probe.utils.subprocess_runner import run as sp_run

        log(f"[srp] LLM ({self.name}): running structured JSON task")
        timeout = load_active_config().llm_timeout_seconds
        result = sp_run(self._build_argv(schema), input=prompt, timeout=timeout)
        return self._parse_response(result.stdout)
