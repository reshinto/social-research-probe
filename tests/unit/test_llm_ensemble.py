"""Tests for social_research_probe/llm/ensemble.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from social_research_probe.llm.ensemble import (
    _build_synthesis_prompt,
    _collect_responses,
    _run_provider,
    _synthesize,
    multi_llm_prompt,
)


def _make_proc(stdout_bytes: bytes = b""):
    """Return a minimal async subprocess mock."""

    class _FakeProc:
        async def communicate(self, input=None):
            return (stdout_bytes, b"")

        async def wait(self):
            return 0

        def kill(self):
            pass

    return _FakeProc()


async def test_run_provider_returns_none_when_command_not_found(monkeypatch):
    """A missing CLI binary should return None, not raise."""

    async def fake_create(*args, **kwargs):
        raise FileNotFoundError("not found")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    assert await _run_provider("claude", "hello") is None


async def test_run_provider_returns_none_on_timeout(monkeypatch):
    async def fake_create(*args, **kwargs):
        return _make_proc(b"answer")

    async def fake_wait_for(coro, timeout):
        coro.close()
        raise TimeoutError()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)
    assert await _run_provider("claude", "hello") is None


async def test_run_provider_returns_none_on_empty_output(monkeypatch):
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_make_proc(b"   "))
    )
    assert await _run_provider("claude", "hello") is None


async def test_run_provider_returns_stripped_output(monkeypatch):
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_make_proc(b"  great answer  "))
    )
    assert await _run_provider("claude", "hello") == "great answer"


async def test_run_provider_unknown_name_returns_none():
    assert await _run_provider("unknown_llm", "hello") is None


async def test_collect_responses_empty_providers_returns_empty_dict():
    """_collect_responses returns {} immediately when providers tuple is empty."""
    assert await _collect_responses("prompt", providers=()) == {}


async def test_collect_responses_returns_only_successes(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    async def fake_run(name: str, prompt: str, task: str = "") -> str | None:
        return "answer" if name == "claude" else None

    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    responses = await _collect_responses("test prompt")
    assert responses == {"claude": "answer"}


async def test_collect_responses_all_fail(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    monkeypatch.setattr(llm_mod, "_run_provider", AsyncMock(return_value=None))
    assert await _collect_responses("test") == {}


async def test_synthesize_none_when_no_responses():
    assert await _synthesize({}, "original") is None


async def test_synthesize_returns_directly_for_single_response():
    result = await _synthesize({"claude": "only answer"}, "prompt")
    assert result == "only answer"


async def test_synthesize_calls_provider_for_multi_response(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    async def fake_run(name, prompt, task=""):
        return "synthesized" if name == "claude" else None

    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    result = await _synthesize({"claude": "a1", "gemini": "a2"}, "prompt")
    assert result == "synthesized"


async def test_synthesize_falls_back_when_claude_synthesis_fails(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    async def fake_run(name, prompt, task=""):
        if name == "gemini":
            return "gemini synthesis"
        return None

    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    result = await _synthesize({"claude": "a1", "gemini": "a2"}, "prompt")
    assert result == "gemini synthesis"


async def test_synthesize_returns_best_single_when_all_synthesis_fail(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    monkeypatch.setattr(llm_mod, "_run_provider", AsyncMock(return_value=None))
    result = await _synthesize({"claude": "claude_direct", "gemini": "gemini_direct"}, "prompt")
    assert result == "claude_direct"


def test_build_synthesis_prompt_contains_original_and_responses():
    prompt = _build_synthesis_prompt("original request", {"claude": "r1", "gemini": "r2"})
    assert "original request" in prompt
    assert "r1" in prompt
    assert "r2" in prompt


async def test_run_provider_local_returns_none_when_bin_not_set(monkeypatch):
    """Local runner returns None when SRP_LOCAL_LLM_BIN is unset."""
    monkeypatch.delenv("SRP_LOCAL_LLM_BIN", raising=False)
    assert await _run_provider("local", "hello") is None


async def test_run_provider_local_calls_binary(monkeypatch):
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/usr/bin/mymodel")
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec", AsyncMock(return_value=_make_proc(b"local answer"))
    )
    assert await _run_provider("local", "hello") == "local answer"


async def test_multi_llm_prompt_disabled_when_runner_is_none(monkeypatch):
    """runner = none must return None without calling any LLM."""
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "none"
        preferred_free_text_runner = None

    async def fake_run(name, p, task=""):
        calls.append(name)
        return "x"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    assert await multi_llm_prompt("anything") is None
    assert calls == []


async def test_multi_llm_prompt_disabled_when_llm_service_off(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = "claude"

        def service_enabled(self, name):
            return name != "llm"

    async def fake_run(name, p, task=""):
        calls.append(name)
        return "x"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    assert await multi_llm_prompt("anything") is None
    assert calls == []


async def test_multi_llm_prompt_returns_none_when_all_fail(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = "claude"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", AsyncMock(return_value=None))
    assert await multi_llm_prompt("anything") is None


async def test_multi_llm_prompt_end_to_end(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = None

    async def fake_run(name: str, prompt: str, task: str = "") -> str | None:
        if "synthesize" in prompt.lower() or "synthesise" in prompt.lower():
            return "final synthesis" if name == "claude" else None
        return f"{name} answer"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    result = await multi_llm_prompt("summarise this video")
    assert result == "final synthesis"


async def test_multi_llm_prompt_uses_configured_provider(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "gemini"
        preferred_free_text_runner = "gemini"

    async def fake_run(name: str, prompt: str, task: str = "") -> str | None:
        calls.append((name, prompt))
        return "configured answer"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)

    assert await multi_llm_prompt("summarise this video") == "configured answer"
    assert calls == [("gemini", "summarise this video")]


async def test_multi_llm_prompt_falls_back_when_configured_provider_fails(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "gemini"
        preferred_free_text_runner = "gemini"

    async def fake_run(name: str, prompt: str, task: str = "") -> str | None:
        calls.append((name, prompt))
        if name == "gemini":
            return None
        if "synthesize" in prompt.lower() or "synthesise" in prompt.lower():
            return "synthesized fallback"
        return "fallback answer"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)

    assert await multi_llm_prompt("summarise this video") == "synthesized fallback"
    assert calls[0] == ("gemini", "summarise this video")
    assert ("claude", "summarise this video") in calls
    assert ("codex", "summarise this video") in calls


async def test_multi_llm_prompt_uses_local_runner(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "local"
        preferred_free_text_runner = "local"

    async def fake_run(name, p, task=""):
        calls.append(name)
        return "local answer"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)

    assert await multi_llm_prompt("summarise this video") == "local answer"
    assert calls == ["local"]


async def test_service_flags_skip_disabled_providers_in_fanout(monkeypatch):
    """Providers with technologies.<name>=false are excluded from the ensemble."""
    from social_research_probe.llm import ensemble as llm_mod

    calls: list[str] = []

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = None

        def service_enabled(self, name):
            return True

        def technology_enabled(self, name):
            return name != "gemini"

    async def fake_run(name, prompt, task=""):
        calls.append(name)
        return f"{name} answer" if "synthesize" not in prompt.lower() else "final"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    result = await multi_llm_prompt("summarise this")
    assert result == "final"
    assert "gemini" not in calls


async def test_primary_runner_always_allowed_when_preferred_runner_is_set(monkeypatch):
    """If preferred_free_text_runner is set, that runner is used directly."""
    from social_research_probe.llm import ensemble as llm_mod

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = "claude"

        def service_enabled(self, name):
            return True

        def technology_enabled(self, name):
            return False

    calls: list[str] = []

    async def fake_run(name, prompt, task=""):
        calls.append(name)
        return "ok"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    assert await multi_llm_prompt("x") == "ok"
    assert calls == ["claude"]


async def test_service_enabled_defaults_true_when_cfg_lacks_technology_gate():
    """Stub Configs without technology_enabled default to allowing every service."""
    from social_research_probe.llm.ensemble import _service_enabled

    class _Stub:
        llm_runner = "none"

    assert _service_enabled(_Stub(), "claude") is True


async def test_service_enabled_returns_false_when_llm_service_off():
    from social_research_probe.llm.ensemble import _service_enabled

    class _Stub:
        llm_runner = "claude"

        def service_enabled(self, name):
            return name != "llm"

    assert _service_enabled(_Stub(), "claude") is False
