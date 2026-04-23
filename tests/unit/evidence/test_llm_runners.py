"""Evidence tests — LLM runner scaffolding + ensemble orchestration.

Phase 0.b tested ``agentic_search`` on every runner. Phase 8 covers the rest
of the runner contract (the structured ``run`` method, ``health_check``
binary probing, ensemble merge/fallback) so the full scaffolding is
evidence-backed before Phase 10's semantic reliability harness is built on
top of it.

| Service | Input | Expected | Why |
| --- | --- | --- | --- |
| JsonCliRunner.health_check | shutil.which returns None | False | CLI missing |
| JsonCliRunner.health_check | shutil.which returns path | True | CLI found |
| Claude.run | canned stdout: {"result": "text"} | parsed dict | envelope parse |
| Claude.run | malformed stdout | AdapterError | documented contract |
| Gemini.run | canned envelope with fenced JSON body | inner parsed JSON | two-layer unwrap |
| multi_llm_prompt | runner='claude' with canned sp_run | response text | single-runner path |
| multi_llm_prompt | runner='none' | None | disabled path |
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from social_research_probe.errors import AdapterError
from social_research_probe.llm.runners.claude import ClaudeRunner
from social_research_probe.llm.runners.gemini import GeminiRunner

# ---------------------------------------------------------------------------
# health_check — binary probing
# ---------------------------------------------------------------------------


def test_claude_health_check_returns_false_when_binary_missing(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.llm.runners.cli_json_base.shutil.which",
        lambda name: None,
    )
    assert ClaudeRunner().health_check() is False


def test_claude_health_check_returns_true_when_binary_present(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.llm.runners.cli_json_base.shutil.which",
        lambda name: "/usr/bin/claude",
    )
    assert ClaudeRunner().health_check() is True


# ---------------------------------------------------------------------------
# run — JSON envelope parsing
# ---------------------------------------------------------------------------


def test_claude_run_parses_json_envelope(monkeypatch):
    envelope = json.dumps({"result": "hello", "extra": "ignored"})

    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout=envelope, stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    result = ClaudeRunner().run("prompt")
    assert result == {"result": "hello", "extra": "ignored"}


def test_claude_run_raises_adapter_error_on_malformed_json(monkeypatch):
    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout="not json at all", stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    with pytest.raises(AdapterError):
        ClaudeRunner().run("prompt")


def test_gemini_run_unwraps_response_envelope_and_parses_inner_json(monkeypatch):
    """Gemini wraps the LLM reply in {'response': '<fenced json>'}; the
    runner must strip both the envelope AND the ```json fence."""
    inner = {"topic": "ai", "confidence": 0.9}
    envelope = json.dumps({"response": f"```json\n{json.dumps(inner)}\n```"})

    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout=envelope, stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    result = GeminiRunner().run("prompt")
    assert result == inner


def test_gemini_run_raises_when_outer_envelope_is_not_json(monkeypatch):
    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout="bare text", stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    with pytest.raises(AdapterError, match="non-JSON envelope"):
        GeminiRunner().run("prompt")


# ---------------------------------------------------------------------------
# multi_llm_prompt — ensemble routing
# ---------------------------------------------------------------------------


class _StubConfig:
    """Minimal config for ensemble routing tests."""

    llm_runner = "claude"
    preferred_free_text_runner = "claude"

    def service_enabled(self, name: str) -> bool:
        return True

    def technology_enabled(self, name: str) -> bool:
        return True


@pytest.mark.anyio
async def test_multi_llm_prompt_returns_none_when_runner_is_none(monkeypatch):
    """config.llm_runner='none' → ensemble short-circuits with None."""
    from social_research_probe.llm import ensemble

    cfg = _StubConfig()
    cfg.llm_runner = "none"
    monkeypatch.setattr(ensemble, "load_active_config", lambda: cfg)
    result = await ensemble.multi_llm_prompt("test prompt")
    assert result is None


@pytest.mark.anyio
async def test_multi_llm_prompt_returns_provider_output_when_runner_is_active(
    monkeypatch,
):
    """Single-runner path: configured provider returns canned text."""
    from social_research_probe.llm import ensemble

    async def _fake_run_provider(name, prompt, task="generating response"):
        return "canned response" if name == "claude" else None

    monkeypatch.setattr(ensemble, "load_active_config", lambda: _StubConfig())
    monkeypatch.setattr(ensemble, "_run_provider", _fake_run_provider)
    result = await ensemble.multi_llm_prompt("test prompt")
    assert result == "canned response"


@pytest.mark.anyio
async def test_multi_llm_prompt_returns_none_when_every_provider_fails(monkeypatch):
    """When the active runner and all enabled services fail, return None."""
    from social_research_probe.llm import ensemble

    async def _fake_run_provider(name, prompt, task="generating response"):
        return None

    monkeypatch.setattr(ensemble, "load_active_config", lambda: _StubConfig())
    monkeypatch.setattr(ensemble, "_run_provider", _fake_run_provider)
    result = await ensemble.multi_llm_prompt("test prompt")
    assert result is None
