"""LLM runner that delegates to a user-specified local binary.

Why this exists: allows operators to plug in any locally-hosted model (e.g.
Ollama, llama.cpp) by pointing SRP_LOCAL_LLM_BIN at the binary path, without
modifying source code. Registered automatically when this module is imported.

Who calls it: llm.registry.get_runner("local"), triggered by importing
llm.runners.
"""

from __future__ import annotations

from social_research_probe.utils.progress import log

import json
import os
from typing import ClassVar

from social_research_probe.errors import AdapterError
from social_research_probe.llm.base import LLMRunner
from social_research_probe.llm.registry import register

# Environment variable that operators set to the absolute path of the local
# LLM binary (e.g. export SRP_LOCAL_LLM_BIN=/usr/local/bin/ollama).
_ENV_VAR = "SRP_LOCAL_LLM_BIN"


@register
class LocalRunner(LLMRunner):
    """Runner that shells out to a local LLM binary specified via env var.

    Purpose: support locally-hosted models without hard-coding binary names.

    Lifecycle: registered at import time via @register; instantiated on demand
    by get_runner("local").

    Who instantiates it: llm.registry.get_runner().

    ABC fulfilled: LLMRunner (health_check, run).
    """

    name: ClassVar[str] = "local"

    def health_check(self) -> bool:
        """Return True if SRP_LOCAL_LLM_BIN is set and the path exists.

        Why both checks: the env var might be set to a path that doesn't exist
        on this machine, which would produce a confusing error at run time.

        Returns:
            True only when the env var is set and the binary file exists on disk.
        """
        bin_path = os.environ.get(_ENV_VAR)
        # Env var missing → runner is not configured.
        if not bin_path:
            return False
        # Env var set but file absent → misconfiguration, not usable.
        return os.path.exists(bin_path)

    def _build_argv(self, schema: dict | None) -> list[str]:
        """Build the argv list for the local LLM binary invocation.

        Why separate: allows unit testing the argument construction without
        actually spawning a subprocess.

        Args:
            schema: Optional JSON schema to pass to the binary via --schema.

        Returns:
            List of strings ready to pass to subprocess_runner.run().

        Note:
            Falls back to an empty string for the binary path if the env var
            is unset; health_check() should gate callers before this point.
        """
        # Read the binary path from the environment at call time so that tests
        # can monkeypatch os.environ without side effects.
        bin_path = os.environ.get(_ENV_VAR, "")
        argv = [bin_path]
        if schema:
            # Serialise the schema dict to a JSON string for the CLI flag.
            argv += ["--schema", json.dumps(schema)]
        return argv

    def _parse_response(self, stdout: str) -> dict:
        """Parse the JSON stdout emitted by the local LLM binary.

        Why separate: unit-testable without a real subprocess call.

        Args:
            stdout: Raw stdout string from the binary.

        Returns:
            Parsed dict from the JSON response.

        Raises:
            AdapterError: If stdout is not valid JSON.
        """
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(f"local LLM returned non-JSON: {stdout[:200]!r}") from exc

    def run(self, prompt: str, *, schema: dict | None = None) -> dict:
        """Send prompt to the local LLM binary and return parsed JSON response.

        Args:
            prompt: The full prompt string; passed to the binary via stdin.
            schema: Optional JSON schema the response must conform to.

        Returns:
            Parsed dict from the LLM's JSON response.

        Raises:
            AdapterError: If the subprocess fails or stdout is not valid JSON.
        """
        from social_research_probe.utils.subprocess_runner import run as sp_run

        argv = self._build_argv(schema)
        log(f"[srp] LLM (local): running structured JSON task via {argv[0]!r}")
        result = sp_run(argv, input=prompt)
        return self._parse_response(result.stdout)
