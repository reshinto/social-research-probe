"""LLM runner that delegates to the Google Gemini CLI.

Why this exists: wraps the `gemini` command-line binary so the pipeline can
send prompts to Gemini without embedding API keys in Python. Registered
automatically when this module is imported.

Who calls it: llm.registry.get_runner("gemini"), triggered by importing
llm.runners.
"""
from __future__ import annotations

import json
import shutil
from typing import ClassVar

from social_research_probe.errors import AdapterError
from social_research_probe.llm.base import LLMRunner
from social_research_probe.llm.registry import register


@register
class GeminiRunner(LLMRunner):
    """Runner that shells out to the `gemini` CLI binary.

    Purpose: send a prompt to Gemini and return the parsed JSON response.

    Lifecycle: registered at import time via @register; instantiated on demand
    by get_runner("gemini").

    Who instantiates it: llm.registry.get_runner().

    ABC fulfilled: LLMRunner (health_check, run).
    """

    name: ClassVar[str] = "gemini"

    def health_check(self) -> bool:
        """Return True if the 'gemini' CLI binary is available on PATH.

        Returns:
            True if shutil.which finds the binary, False otherwise.
        """
        return shutil.which("gemini") is not None

    def _build_argv(self, schema: dict | None) -> list[str]:
        """Build the argv list for the gemini CLI invocation.

        Why separate: allows unit testing the argument construction without
        actually spawning a subprocess.

        Args:
            schema: Optional JSON schema to pass to the CLI via --schema.

        Returns:
            List of strings ready to pass to subprocess_runner.run().
        """
        # Base invocation: request JSON-formatted output from the gemini CLI.
        argv = ["gemini", "--format", "json"]
        if schema:
            # Serialise the schema dict to a JSON string for the CLI flag.
            argv += ["--schema", json.dumps(schema)]
        return argv

    def _parse_response(self, stdout: str) -> dict:
        """Parse the JSON stdout emitted by the gemini CLI.

        Why separate: unit-testable without a real subprocess call.

        Args:
            stdout: Raw stdout string from the CLI.

        Returns:
            Parsed dict from the JSON response.

        Raises:
            AdapterError: If stdout is not valid JSON.
        """
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise AdapterError(
                f"gemini returned non-JSON: {stdout[:200]!r}"
            ) from exc

    def run(self, prompt: str, *, schema: dict | None = None) -> dict:  # pragma: no cover — live subprocess
        """Send prompt to the gemini CLI and return parsed JSON response.

        Args:
            prompt: The full prompt string; passed to the CLI via stdin.
            schema: Optional JSON schema the response must conform to.

        Returns:
            Parsed dict from the LLM's JSON response.

        Raises:
            AdapterError: If the subprocess fails or stdout is not valid JSON.
        """
        from social_research_probe.utils.subprocess_runner import run as sp_run

        argv = self._build_argv(schema)
        result = sp_run(argv, input=prompt)
        return self._parse_response(result.stdout)
