"""Tests for social_research_probe/llm/ensemble.py."""

from __future__ import annotations

from social_research_probe.llm.ensemble import (
    _build_synthesis_prompt,
    _collect_responses,
    _run_provider,
    _synthesize,
    multi_llm_prompt,
)


def test_run_provider_returns_none_when_command_not_found(monkeypatch):
    """A missing CLI binary should return None, not raise."""
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("not found")),
    )
    assert _run_provider("claude", "hello") is None


def test_run_provider_returns_none_on_timeout(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired(["claude"], 60)),
    )
    assert _run_provider("claude", "hello") is None


def test_run_provider_returns_none_on_empty_output(monkeypatch):
    import subprocess

    class _Result:
        stdout = "   "

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _Result())
    assert _run_provider("claude", "hello") is None


def test_run_provider_returns_stripped_output(monkeypatch):
    import subprocess

    class _Result:
        stdout = "  great answer  "

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _Result())
    assert _run_provider("claude", "hello") == "great answer"


def test_run_provider_unknown_name_returns_none():
    assert _run_provider("unknown_llm", "hello") is None


def test_collect_responses_returns_only_successes(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    def fake_run(name: str, prompt: str) -> str | None:
        return "answer" if name == "claude" else None

    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    responses = _collect_responses("test prompt")
    assert responses == {"claude": "answer"}


def test_collect_responses_all_fail(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    monkeypatch.setattr(llm_mod, "_run_provider", lambda name, prompt: None)
    assert _collect_responses("test") == {}


def test_synthesize_none_when_no_responses():
    assert _synthesize({}, "original") is None


def test_synthesize_returns_directly_for_single_response():
    result = _synthesize({"claude": "only answer"}, "prompt")
    assert result == "only answer"


def test_synthesize_calls_provider_for_multi_response(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    monkeypatch.setattr(
        llm_mod, "_run_provider", lambda name, prompt: "synthesized" if name == "claude" else None
    )
    result = _synthesize({"claude": "a1", "gemini": "a2"}, "prompt")
    assert result == "synthesized"


def test_synthesize_falls_back_when_claude_synthesis_fails(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    def fake_run(name, prompt):
        if name == "gemini":
            return "gemini synthesis"
        return None

    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    result = _synthesize({"claude": "a1", "gemini": "a2"}, "prompt")
    assert result == "gemini synthesis"


def test_synthesize_returns_best_single_when_all_synthesis_fail(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    monkeypatch.setattr(llm_mod, "_run_provider", lambda name, prompt: None)
    result = _synthesize({"claude": "claude_direct", "gemini": "gemini_direct"}, "prompt")
    assert result == "claude_direct"


def test_build_synthesis_prompt_contains_original_and_responses():
    prompt = _build_synthesis_prompt("original request", {"claude": "r1", "gemini": "r2"})
    assert "original request" in prompt
    assert "r1" in prompt
    assert "r2" in prompt


def test_run_provider_local_returns_none_when_bin_not_set(monkeypatch):
    """Local runner returns None when SRP_LOCAL_LLM_BIN is unset."""
    monkeypatch.delenv("SRP_LOCAL_LLM_BIN", raising=False)
    assert _run_provider("local", "hello") is None


def test_run_provider_local_calls_binary(monkeypatch):
    import subprocess

    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/usr/bin/mymodel")

    class _Result:
        stdout = "local answer"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _Result())
    assert _run_provider("local", "hello") == "local answer"


def test_multi_llm_prompt_disabled_when_runner_is_none(monkeypatch):
    """runner = none must return None without calling any LLM."""
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "none"
        preferred_free_text_runner = None

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", lambda name, p: calls.append(name) or "x")
    assert multi_llm_prompt("anything") is None
    assert calls == []


def test_multi_llm_prompt_returns_none_when_all_fail(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = "claude"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", lambda name, prompt: None)
    assert multi_llm_prompt("anything") is None


def test_multi_llm_prompt_end_to_end(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    class _FakeConfig:
        llm_runner = "claude"
        preferred_free_text_runner = None  # simulate unknown runner → triggers ensemble

    def fake_run(name: str, prompt: str) -> str | None:
        if "synthesize" in prompt.lower() or "synthesise" in prompt.lower():
            return "final synthesis" if name == "claude" else None
        return f"{name} answer"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)
    result = multi_llm_prompt("summarise this video")
    assert result == "final synthesis"


def test_multi_llm_prompt_uses_configured_provider(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "gemini"
        preferred_free_text_runner = "gemini"

    def fake_run(name: str, prompt: str) -> str | None:
        calls.append((name, prompt))
        return "configured answer"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", fake_run)

    assert multi_llm_prompt("summarise this video") == "configured answer"
    assert calls == [("gemini", "summarise this video")]


def test_multi_llm_prompt_uses_local_runner(monkeypatch):
    from social_research_probe.llm import ensemble as llm_mod

    calls = []

    class _FakeConfig:
        llm_runner = "local"
        preferred_free_text_runner = "local"

    monkeypatch.setattr(llm_mod, "load_active_config", lambda: _FakeConfig())
    monkeypatch.setattr(llm_mod, "_run_provider", lambda name, p: calls.append(name) or "local answer")

    assert multi_llm_prompt("summarise this video") == "local answer"
    assert calls == ["local"]
