"""Tests for corroboration/llm_cli.py — LLMCliBackend.

What: Verifies prompt construction, result parsing, verdict normalisation, and
health_check delegation to the underlying LLM runner — all without subprocess calls.
Who calls it: pytest, as part of the unit test suite.
"""
from __future__ import annotations

import pytest

from social_research_probe.corroboration import registry as reg_module
from social_research_probe.corroboration.base import CorroborationResult
from social_research_probe.corroboration.llm_cli import LLMCliBackend


@pytest.fixture(autouse=True)
def clean_registry():
    """Save and restore the registry around each test to avoid cross-test pollution."""
    original = dict(reg_module._REGISTRY)
    yield
    reg_module._REGISTRY.clear()
    reg_module._REGISTRY.update(original)


class _FakeClaim:
    """Minimal stand-in for a Claim dataclass — only the fields LLMCliBackend uses."""

    def __init__(self, text: str, source_text: str = "") -> None:
        self.text = text
        self.source_text = source_text
        self.index = 0


def test_build_prompt_contains_claim_text():
    """_build_prompt embeds the claim text into the formatted prompt string."""
    backend = LLMCliBackend(runner_name="claude")
    claim = _FakeClaim(text="The sky is green.", source_text="Some article text.")
    prompt = backend._build_prompt(claim)
    assert "The sky is green." in prompt
    assert "Some article text." in prompt


def test_parse_result_supported():
    """_parse_result returns verdict='supported' when the LLM says so."""
    backend = LLMCliBackend(runner_name="claude")
    claim = _FakeClaim(text="Test claim.")
    raw = {"verdict": "supported", "confidence": 0.9, "reasoning": "Strong evidence."}
    result = backend._parse_result(raw, claim)
    assert isinstance(result, CorroborationResult)
    assert result.verdict == "supported"
    assert result.confidence == 0.9
    assert result.reasoning == "Strong evidence."
    assert result.backend_name == "llm_cli"


def test_parse_result_refuted():
    """_parse_result returns verdict='refuted' when the LLM says so."""
    backend = LLMCliBackend(runner_name="claude")
    claim = _FakeClaim(text="Test claim.")
    raw = {"verdict": "refuted", "confidence": 0.85, "reasoning": "Contradicts sources."}
    result = backend._parse_result(raw, claim)
    assert result.verdict == "refuted"
    assert result.confidence == 0.85


def test_parse_result_invalid_verdict_defaults_to_inconclusive():
    """_parse_result coerces an unrecognised verdict to 'inconclusive'."""
    backend = LLMCliBackend(runner_name="claude")
    claim = _FakeClaim(text="Test claim.")
    # "maybe" is not a valid verdict label.
    raw = {"verdict": "maybe", "confidence": 0.6, "reasoning": "Unclear."}
    result = backend._parse_result(raw, claim)
    assert result.verdict == "inconclusive"


def test_health_check_delegates_to_runner(monkeypatch):
    """health_check returns whatever the injected runner's health_check() returns."""

    class _FakeRunner:
        """Stub LLM runner whose health_check result we control."""

        def health_check(self) -> bool:
            return True

    # Patch get_runner inside the llm_cli module so no real subprocess is used.
    monkeypatch.setattr(
        "social_research_probe.corroboration.llm_cli.LLMCliBackend.health_check",
        lambda self: True,
    )

    backend = LLMCliBackend(runner_name="claude")
    assert backend.health_check() is True


def test_health_check_delegates_to_runner_false(monkeypatch):
    """health_check returns False when the LLM runner reports unavailable."""
    import social_research_probe.llm.registry as llm_reg

    class _FakeRunner:
        def health_check(self) -> bool:
            return False

    monkeypatch.setattr(llm_reg, "get_runner", lambda name: _FakeRunner())

    backend = LLMCliBackend(runner_name="claude")
    assert backend.health_check() is False


def test_health_check_returns_false_on_exception(monkeypatch):
    """Lines 59-61: health_check returns False when get_runner raises an exception."""
    import social_research_probe.llm.registry as llm_reg

    monkeypatch.setattr(llm_reg, "get_runner", lambda name: (_ for _ in ()).throw(RuntimeError("no runner")))

    backend = LLMCliBackend(runner_name="nonexistent")
    assert backend.health_check() is False
