"""Live integration tests — verify that Claude, Gemini, and Codex runners respond.

Run manually when checking LLM availability:

    pytest tests/integration/test_llm_runner_health.py -v

These tests shell out to the real CLIs and require network/auth. They are
excluded from the default test run (no marker required by CI config).
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

_PING_PROMPT = "Reply with exactly one word: PONG"
_TIMEOUT = 90  # seconds — Codex can be slow on first call
_RUN_LIVE = os.environ.get("SRP_RUN_LLM_LIVE_TESTS") == "1"


def _run(cmd: list[str], stdin_devnull: bool = False) -> tuple[int, str, str]:
    """Run *cmd* and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL if stdin_devnull else None,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@pytest.mark.skipif(
    not _RUN_LIVE or shutil.which("claude") is None,
    reason="set SRP_RUN_LLM_LIVE_TESTS=1 and install claude CLI",
)
def test_claude_cli_responds():
    """Claude Code CLI (`claude -p`) returns a non-empty response."""
    rc, out, err = _run(["claude", "-p", _PING_PROMPT], stdin_devnull=True)
    assert rc == 0, f"claude exited {rc}\nstderr: {err}"
    assert out, f"claude returned empty stdout\nstderr: {err}"
    print(f"\nclaude response: {out!r}")


@pytest.mark.skipif(
    not _RUN_LIVE or shutil.which("gemini") is None,
    reason="set SRP_RUN_LLM_LIVE_TESTS=1 and install gemini CLI",
)
def test_gemini_cli_responds():
    """Gemini CLI (`gemini -p`) returns a non-empty response."""
    rc, out, err = _run(["gemini", "-p", _PING_PROMPT])
    assert rc == 0, f"gemini exited {rc}\nstderr: {err}"
    assert out, f"gemini returned empty stdout\nstderr: {err}"
    print(f"\ngemini response: {out!r}")


@pytest.mark.skipif(
    not _RUN_LIVE or shutil.which("codex") is None,
    reason="set SRP_RUN_LLM_LIVE_TESTS=1 and install codex CLI",
)
def test_codex_cli_responds():
    """Codex CLI (`codex exec`) returns a non-empty response on stdout."""
    rc, out, err = _run(["codex", "exec", _PING_PROMPT], stdin_devnull=True)
    assert rc == 0, f"codex exited {rc}\nstderr: {err}"
    assert out, f"codex returned empty stdout\nstderr: {err}"
    print(f"\ncodex response: {out!r}")


@pytest.mark.skipif(
    not _RUN_LIVE or all(shutil.which(cli) is None for cli in ("claude", "gemini", "codex")),
    reason="set SRP_RUN_LLM_LIVE_TESTS=1 and install at least one LLM CLI",
)
def test_ensemble_multi_llm_prompt_live():
    """End-to-end: multi_llm_prompt fans out to all available CLIs and synthesizes."""
    from social_research_probe.llm.ensemble import multi_llm_prompt

    result = multi_llm_prompt(
        "In 2-3 sentences, explain what a transformer neural network is. Be concise."
    )
    assert result is not None, "multi_llm_prompt returned None — all providers failed"
    assert len(result.split()) >= 10, f"Response too short to be a real answer: {result!r}"
    print(f"\nensemble result ({len(result.split())} words):\n{result}")
