"""Evidence test — corroboration search routes through the LLM runner abstraction.

The ``llm_search`` backend must dispatch through the configured runner —
every runner with agentic-search support can drive corroboration, not
just Gemini. The invariant we test here is: **the backend dispatches via
``config.llm_runner``**, and if the runner does not support agentic search
the backend reports ``health_check()`` False so the host skips it instead of
returning false evidence.

Evidence receipt (what / expected / why):

| Case | Input (config.llm_runner, runner.supports_agentic_search, health_check) | Expected | Why |
| --- | --- | --- | --- |
| Gemini routing | ``"gemini"``, True, True; runner.agentic_search returns {answer: "supported", citations: [arxiv, youtube]} | backend.health_check() True; corroborate returns verdict=``supported``, sources=``["arxiv"]`` | runner resolver picks gemini; youtube citation is filtered by Phase 0.a video-domain rule |
| Claude routing | ``"claude"``, True, True; runner.agentic_search returns {answer: "refuted", citations: [nature]} | backend.health_check() True; corroborate calls claude runner's agentic_search; verdict=``refuted``, sources=``["nature"]`` | same resolver selects claude instead of gemini; proves no hard-coded LLM |
| Local runner | ``"local"``, False (default on base), n/a | backend.health_check() False; corroborate returns verdict=``inconclusive`` with reason mentioning agentic_search | local runner cannot perform web search; host should skip the backend |
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from social_research_probe.corroboration.llm_search import (
    LLMSearchBackend,
    _classify_verdict,
    _resolve_active_runner,
)
from social_research_probe.errors import AdapterError
from social_research_probe.llm.base import CapabilityUnavailableError
from social_research_probe.llm.runners.claude import ClaudeRunner
from social_research_probe.llm.runners.codex import CodexRunner
from social_research_probe.llm.runners.gemini import GeminiRunner
from social_research_probe.llm.runners.local import LocalRunner
from social_research_probe.llm.types import AgenticSearchCitation, AgenticSearchResult
from social_research_probe.validation.claims import Claim

from social_research_probe.technologies.llms.codex_cli import CodexCliFlag


class _StubConfig:
    """Minimal active-config stub used by the backend's runner resolver."""

    def __init__(
        self,
        runner_name: str,
        *,
        llm_enabled: bool = True,
        technologies: dict[str, bool] | None = None,
    ) -> None:
        self.llm_runner = runner_name
        self._llm_enabled = llm_enabled
        self._technologies = technologies or {}

    def service_enabled(self, name: str) -> bool:
        return self._llm_enabled if name == "llm" else True

    def technology_enabled(self, name: str) -> bool:
        return self._technologies.get(name, True)


class _StubRunner:
    """Simulates an LLM runner with a deterministic ``agentic_search``."""

    def __init__(
        self,
        *,
        name: str,
        supports: bool,
        healthy: bool,
        result: AgenticSearchResult | None = None,
    ) -> None:
        self.name = name
        self.supports_agentic_search = supports
        self._healthy = healthy
        self._result = result

    def health_check(self) -> bool:
        return self._healthy

    async def agentic_search(
        self,
        query: str,
        *,
        max_results: int = 5,
        timeout_s: float = 60.0,
    ) -> AgenticSearchResult:
        if self._result is None:
            raise CapabilityUnavailableError("stubbed runner has no canned result")
        return self._result


def _install_runner(monkeypatch, runner_name: str, runner: _StubRunner | None) -> None:
    """Redirect the backend's config and registry lookups to the stubs."""
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.load_active_config",
        lambda: _StubConfig(runner_name),
    )

    def _get_runner(name: str):
        assert name == runner_name, f"backend asked for {name!r} not {runner_name!r}"
        if runner is None:
            raise KeyError(name)
        return runner

    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.get_runner",
        _get_runner,
    )


def _claim(source_url: str | None = None) -> Claim:
    return Claim(
        text="GPT-4 was released in March 2023.",
        source_text="GPT-4 was released in March 2023.",
        index=0,
        source_url=source_url,
    )


@pytest.mark.anyio
async def test_active_runner_gemini_drives_agentic_search(monkeypatch):
    """When config.llm_runner is 'gemini', the backend calls gemini's agentic_search."""
    canned = AgenticSearchResult(
        answer="This claim is supported by the following sources.",
        citations=[
            AgenticSearchCitation(url="https://arxiv.org/abs/2303.08774"),
            AgenticSearchCitation(url="https://www.youtube.com/watch?v=abc"),
        ],
        runner_name="gemini",
    )
    runner = _StubRunner(name="gemini", supports=True, healthy=True, result=canned)
    _install_runner(monkeypatch, "gemini", runner)

    backend = LLMSearchBackend()
    assert backend.health_check() is True
    result = await backend.corroborate(_claim(source_url="https://example.com/post"))
    assert result.verdict == "supported"
    assert result.sources == ["https://arxiv.org/abs/2303.08774"]


@pytest.mark.anyio
async def test_active_runner_claude_drives_agentic_search(monkeypatch):
    """Switching config to 'claude' routes the same backend through claude."""
    canned = AgenticSearchResult(
        answer="This claim is refuted by recent peer-reviewed research.",
        citations=[
            AgenticSearchCitation(url="https://www.nature.com/articles/x"),
        ],
        runner_name="claude",
    )
    runner = _StubRunner(name="claude", supports=True, healthy=True, result=canned)
    _install_runner(monkeypatch, "claude", runner)

    backend = LLMSearchBackend()
    assert backend.health_check() is True
    result = await backend.corroborate(_claim())
    assert result.verdict == "refuted"
    assert result.sources == ["https://www.nature.com/articles/x"]


@pytest.mark.anyio
async def test_local_runner_does_not_support_agentic_search(monkeypatch):
    """Local runner has supports_agentic_search=False; backend reports unhealthy."""
    runner = _StubRunner(name="local", supports=False, healthy=True)
    _install_runner(monkeypatch, "local", runner)

    backend = LLMSearchBackend()
    assert backend.health_check() is False
    result = await backend.corroborate(_claim())
    assert result.verdict == "inconclusive"
    assert result.confidence == 0.0
    assert "agentic_search" in result.reasoning


@pytest.mark.anyio
async def test_runner_none_config_skips_cleanly(monkeypatch):
    """config.llm_runner='none' resolves to no runner; backend stays safe."""
    _install_runner(monkeypatch, "none", None)
    backend = LLMSearchBackend()
    assert backend.health_check() is False
    result = await backend.corroborate(_claim())
    assert result.verdict == "inconclusive"
    assert result.sources == []


@pytest.mark.anyio
async def test_llm_service_disabled_skips_llm_search(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.load_active_config",
        lambda: _StubConfig("gemini", llm_enabled=False),
    )
    backend = LLMSearchBackend()
    assert backend.health_check() is False
    result = await backend.corroborate(_claim())
    assert result.verdict == "inconclusive"
    assert result.sources == []


def test_resolve_active_runner_returns_none_when_llm_search_technology_disabled(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.load_active_config",
        lambda: _StubConfig("gemini", technologies={"llm_search": False}),
    )
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.get_runner",
        lambda name: (_ for _ in ()).throw(AssertionError("runner lookup should be skipped")),
    )
    assert _resolve_active_runner() is None


def test_resolve_active_runner_returns_none_when_runner_technology_disabled(monkeypatch):
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.load_active_config",
        lambda: _StubConfig("gemini", technologies={"gemini": False}),
    )
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.get_runner",
        lambda name: (_ for _ in ()).throw(AssertionError("runner lookup should be skipped")),
    )
    assert _resolve_active_runner() is None


@pytest.mark.parametrize(
    "answer, expected_verdict, min_conf, max_conf",
    [
        ("The evidence strongly supports the claim.", "supported", 0.5, 0.9),
        ("This claim is false and has been refuted.", "refuted", 0.5, 0.9),
        ("Some truth but partially misleading.", "inconclusive", 0.5, 0.5),
        ("The sky is blue and grass is green.", "inconclusive", 0.3, 0.3),
    ],
)
def test_classify_verdict_rules(answer, expected_verdict, min_conf, max_conf):
    """Verdict classifier maps keyword families to verdict + bounded confidence."""
    verdict, confidence = _classify_verdict(answer)
    assert verdict == expected_verdict
    assert min_conf <= confidence <= max_conf


@pytest.mark.anyio
async def test_runner_health_check_raising_is_treated_as_unhealthy(monkeypatch):
    """A runner whose health_check raises must not crash the backend."""

    class _Raising(_StubRunner):
        def health_check(self) -> bool:
            raise RuntimeError("broken")

    runner = _Raising(name="gemini", supports=True, healthy=True)
    _install_runner(monkeypatch, "gemini", runner)
    backend = LLMSearchBackend()
    assert backend.health_check() is False


@pytest.mark.anyio
async def test_backend_unknown_runner_name_skips_cleanly(monkeypatch):
    """When get_runner raises KeyError (bad config), backend treats as skip."""
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.load_active_config",
        lambda: _StubConfig("nonexistent"),
    )

    def _raise_key_error(name: str):
        raise KeyError(name)

    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_search.get_runner",
        _raise_key_error,
    )
    backend = LLMSearchBackend()
    assert backend.health_check() is False
    result = await backend.corroborate(_claim())
    assert result.verdict == "inconclusive"


@pytest.mark.anyio
async def test_backend_adapter_error_from_runner_produces_inconclusive(monkeypatch):
    """Runner raising AdapterError doesn't crash the backend."""

    class _Failing(_StubRunner):
        async def agentic_search(self, query, *, max_results=5, timeout_s=60.0):
            raise AdapterError("network down")

    runner = _Failing(name="gemini", supports=True, healthy=True)
    _install_runner(monkeypatch, "gemini", runner)
    backend = LLMSearchBackend()
    result = await backend.corroborate(_claim())
    assert result.verdict == "inconclusive"
    assert "agentic_search failed" in result.reasoning


@pytest.mark.anyio
async def test_default_agentic_search_raises_capability_unavailable():
    """Runners that don't override must raise CapabilityUnavailableError on call."""
    runner = LocalRunner()
    with pytest.raises(CapabilityUnavailableError):
        await runner.agentic_search("any query")


# Per-runner agentic_search happy-path + error-path tests. These exercise the
# vendor-specific scaffolding with canned stdout — Phase 8 adds broader
# coverage in tests/evidence/test_llm_runners.py.


@pytest.mark.anyio
async def test_gemini_runner_agentic_search_returns_structured_result(monkeypatch):
    async def _fake_gemini_search(query, *, timeout_s=60.0):
        return {
            "answer": "Supported by peer-reviewed sources.",
            "citations": [
                {"url": "https://arxiv.org/abs/1", "title": "Paper"},
                {"url": "", "title": "skip me"},
            ],
        }

    monkeypatch.setattr("social_research_probe.llm.gemini_cli.gemini_search", _fake_gemini_search)
    runner = GeminiRunner()
    result = await runner.agentic_search("test claim", max_results=5)
    assert result.runner_name == "gemini"
    assert result.answer.startswith("Supported")
    assert [c.url for c in result.citations] == ["https://arxiv.org/abs/1"]


@pytest.mark.anyio
async def test_claude_runner_agentic_search_parses_structured_json(monkeypatch):
    envelope = json.dumps(
        {
            "result": json.dumps(
                {
                    "answer": "Claim refuted by nature.com.",
                    "citations": [
                        {"url": "https://www.nature.com/x", "title": "Nature"},
                        {"title": "missing url"},
                    ],
                }
            )
        }
    )

    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout=envelope, stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.llm.runners.claude.sp_run", _fake_sp_run)
    runner = ClaudeRunner()
    result = await runner.agentic_search("test claim", max_results=5)
    assert result.runner_name == "claude"
    assert result.answer.startswith("Claim refuted")
    assert [c.url for c in result.citations] == ["https://www.nature.com/x"]


@pytest.mark.anyio
async def test_claude_runner_agentic_search_falls_back_to_url_extraction(monkeypatch):
    envelope = json.dumps(
        {"result": "See https://arxiv.org/abs/2 and https://example.com/a for details."}
    )

    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout=envelope, stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.llm.runners.claude.sp_run", _fake_sp_run)
    runner = ClaudeRunner()
    result = await runner.agentic_search("test", max_results=5)
    assert {c.url for c in result.citations} == {
        "https://arxiv.org/abs/2",
        "https://example.com/a",
    }


@pytest.mark.anyio
async def test_claude_runner_agentic_search_wraps_subprocess_error(monkeypatch):
    def _fake_sp_run(argv, *, timeout, input=None):
        raise AdapterError("subprocess exploded")

    monkeypatch.setattr("social_research_probe.llm.runners.claude.sp_run", _fake_sp_run)
    runner = ClaudeRunner()
    with pytest.raises(AdapterError, match="claude agentic_search failed"):
        await runner.agentic_search("test")


@pytest.mark.anyio
async def test_claude_runner_agentic_search_non_string_result(monkeypatch):
    """Envelope 'result' that isn't a string becomes empty body, no citations."""

    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout=json.dumps({"result": 123}), stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.llm.runners.claude.sp_run", _fake_sp_run)
    runner = ClaudeRunner()
    result = await runner.agentic_search("test")
    assert result.answer == ""
    assert result.citations == []


@pytest.mark.anyio
async def test_codex_runner_agentic_search_parses_last_message_file(monkeypatch):
    from pathlib import Path

    payload = {
        "answer": "Claim is consistent with multiple sources.",
        "citations": [
            {"url": "https://arxiv.org/abs/3", "title": "A"},
            {"title": "no url"},
        ],
    }

    def _fake_sp_run(argv, *, timeout, input=None):
        out_path = argv[argv.index(CodexCliFlag.OUTPUT_LAST_MESSAGE) + 1]
        Path(out_path).write_text(json.dumps(payload), encoding="utf-8")
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    runner = CodexRunner()
    result = await runner.agentic_search("test", max_results=5)
    assert result.runner_name == "codex"
    assert result.answer.startswith("Claim is consistent")
    assert [c.url for c in result.citations] == ["https://arxiv.org/abs/3"]


@pytest.mark.anyio
async def test_codex_runner_agentic_search_wraps_json_error(monkeypatch):
    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout="not json", stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    runner = CodexRunner()
    with pytest.raises(AdapterError, match="codex agentic_search failed"):
        await runner.agentic_search("test")


@pytest.mark.anyio
async def test_codex_runner_agentic_search_non_dict_payload(monkeypatch):
    """Valid JSON list (non-dict) yields empty answer and no citations."""

    def _fake_sp_run(argv, *, timeout, input=None):
        return SimpleNamespace(stdout=json.dumps([1, 2, 3]), stderr="", returncode=0)

    monkeypatch.setattr("social_research_probe.utils.subprocess_runner.run", _fake_sp_run)
    runner = CodexRunner()
    result = await runner.agentic_search("test")
    assert result.answer == ""
    assert result.citations == []
