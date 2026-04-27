"""Cover ensemble._run_provider subprocess paths and multi_llm_prompt fallback."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from social_research_probe.services.llm import ensemble


class _FakeProc:
    def __init__(self, output=b"hello\n", raise_timeout=False, raise_exc=False):
        self._output = output
        self._raise_timeout = raise_timeout
        self._raise_exc = raise_exc

    async def communicate(self, stdin=None):
        if self._raise_timeout:
            raise TimeoutError
        if self._raise_exc:
            raise RuntimeError("boom")
        return self._output, b""

    def kill(self):
        pass

    async def wait(self):
        pass


@pytest.fixture
def fake_subproc(monkeypatch):
    holder = {"output": b"hello\n", "timeout": False, "exc": False}

    async def fake_create(*a, **kw):
        return _FakeProc(holder["output"], holder["timeout"], holder["exc"])

    monkeypatch.setattr(ensemble.asyncio, "create_subprocess_exec", fake_create)
    return holder


def test_run_provider_claude(fake_subproc):
    out = asyncio.run(ensemble._run_provider("claude", "p"))
    assert out == "hello"


def test_run_provider_gemini(fake_subproc):
    out = asyncio.run(ensemble._run_provider("gemini", "p"))
    assert out == "hello"


def test_run_provider_codex(fake_subproc):
    out = asyncio.run(ensemble._run_provider("codex", "p"))
    assert out == "hello"


def test_run_provider_local(fake_subproc, monkeypatch):
    monkeypatch.setenv("SRP_LOCAL_LLM_BIN", "/usr/bin/local-llm")
    out = asyncio.run(ensemble._run_provider("local", "p"))
    assert out == "hello"


def test_run_provider_timeout(fake_subproc):
    fake_subproc["timeout"] = True
    out = asyncio.run(ensemble._run_provider("claude", "p"))
    assert out is None


def test_run_provider_empty_output(fake_subproc):
    fake_subproc["output"] = b""
    out = asyncio.run(ensemble._run_provider("claude", "p"))
    assert out is None


def test_run_provider_exception(fake_subproc):
    fake_subproc["exc"] = True
    out = asyncio.run(ensemble._run_provider("claude", "p"))
    assert out is None


def test_multi_llm_prompt_preferred_fallback(monkeypatch):
    cfg = MagicMock()
    cfg.service_enabled.return_value = True
    cfg.llm_runner = "claude"
    cfg.preferred_free_text_runner = "claude"
    cfg.technology_enabled.return_value = True

    async def fake_run(name, prompt, task="generating response"):
        # Preferred fails → fallback runs collect
        return None

    async def fake_collect(prompt, task, providers):
        return {"gemini": "g"}

    async def fake_synth(responses, prompt, cfg=None):
        return responses["gemini"]

    monkeypatch.setattr(ensemble, "_run_provider", fake_run)
    monkeypatch.setattr(ensemble, "_collect_responses", fake_collect)
    monkeypatch.setattr(ensemble, "_synthesize", fake_synth)
    with patch.object(ensemble, "load_active_config", return_value=cfg):
        out = asyncio.run(ensemble.multi_llm_prompt("p"))
    assert out == "g"


def test_multi_llm_prompt_local_preferred(monkeypatch):
    cfg = MagicMock()
    cfg.service_enabled.return_value = True
    cfg.llm_runner = "local"
    cfg.preferred_free_text_runner = "local"
    cfg.technology_enabled.return_value = True

    async def fake_run(name, prompt, task="generating response"):
        return None

    async def fake_collect(prompt, task, providers):
        return {"claude": "c"}

    async def fake_synth(responses, prompt, cfg=None):
        return responses["claude"]

    monkeypatch.setattr(ensemble, "_run_provider", fake_run)
    monkeypatch.setattr(ensemble, "_collect_responses", fake_collect)
    monkeypatch.setattr(ensemble, "_synthesize", fake_synth)
    with patch.object(ensemble, "load_active_config", return_value=cfg):
        out = asyncio.run(ensemble.multi_llm_prompt("p"))
    assert out == "c"


def test_service_enabled_primary_runner(monkeypatch):
    cfg = MagicMock()
    cfg.service_enabled.return_value = True
    cfg.technology_enabled.return_value = False  # secondary disabled
    cfg.llm_runner = "claude"
    # claude is primary; should be allowed
    assert ensemble._service_enabled(cfg, "claude") is False  # tech disabled returns False


def test_service_enabled_no_method():
    class Cfg:
        llm_runner = "claude"

    assert ensemble._service_enabled(Cfg(), "claude") is True
