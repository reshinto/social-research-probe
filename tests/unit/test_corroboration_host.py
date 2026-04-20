"""Tests for corroboration/host.py — aggregate_verdict and corroborate_claim.

What: Verifies majority-vote logic, tie-breaking, weighted-average confidence,
and that AdapterError from a backend does not abort the whole run.
Who calls it: pytest, as part of the unit test suite.
"""

from __future__ import annotations

import pytest

from social_research_probe.corroboration import registry as reg_module
from social_research_probe.corroboration.base import CorroborationBackend, CorroborationResult
from social_research_probe.corroboration.host import aggregate_verdict, corroborate_claim
from social_research_probe.errors import AdapterError
from social_research_probe.validation.claims import Claim


@pytest.fixture(autouse=True)
def clean_registry():
    """Save and restore the registry around each test."""
    original = dict(reg_module._REGISTRY)
    yield
    reg_module._REGISTRY.clear()
    reg_module._REGISTRY.update(original)


def _result(verdict: str, confidence: float) -> CorroborationResult:
    """Shorthand factory for CorroborationResult."""
    return CorroborationResult(verdict=verdict, confidence=confidence, reasoning="test")


def test_aggregate_verdict_supported_majority():
    """Majority 'supported' votes produce verdict='supported'."""
    results = [
        _result("supported", 0.9),
        _result("supported", 0.8),
        _result("refuted", 0.5),
    ]
    verdict, _ = aggregate_verdict(results)
    assert verdict == "supported"


def test_aggregate_verdict_refuted_majority():
    """Majority 'refuted' votes produce verdict='refuted'."""
    results = [
        _result("refuted", 0.7),
        _result("refuted", 0.6),
        _result("supported", 0.4),
    ]
    verdict, _ = aggregate_verdict(results)
    assert verdict == "refuted"


def test_aggregate_verdict_tie_goes_to_inconclusive():
    """An exact tie between two verdicts resolves to 'inconclusive'."""
    results = [
        _result("supported", 0.8),
        _result("refuted", 0.8),
    ]
    verdict, _ = aggregate_verdict(results)
    assert verdict == "inconclusive"


def test_aggregate_confidence_weighted_average():
    """Aggregate confidence is the weighted average of individual confidences."""
    # Both results have the same verdict so majority is clear.
    # confidence = (0.9*0.9 + 0.1*0.1) / (0.9 + 0.1) = (0.81 + 0.01) / 1.0 = 0.82
    results = [
        _result("supported", 0.9),
        _result("supported", 0.1),
    ]
    _, confidence = aggregate_verdict(results)
    assert abs(confidence - 0.82) < 1e-6


async def test_corroborate_claim_skips_failed_backend(capsys):
    """A backend that raises AdapterError is skipped; the run still returns results."""

    # Register a failing backend.
    class _FailingBackend(CorroborationBackend):
        name = "failing_test_backend"

        def health_check(self) -> bool:
            return True

        async def corroborate(self, claim) -> CorroborationResult:
            raise AdapterError("simulated failure")

    reg_module.register(_FailingBackend)

    # Register a working backend.
    class _OkBackend(CorroborationBackend):
        name = "ok_test_backend"

        def health_check(self) -> bool:
            return True

        async def corroborate(self, claim) -> CorroborationResult:
            return CorroborationResult(verdict="supported", confidence=0.7, reasoning="ok")

    reg_module.register(_OkBackend)

    claim = Claim(text="Test claim text.", source_text="Some source.", index=0)
    result = await corroborate_claim(claim, ["failing_test_backend", "ok_test_backend"])

    # The failing backend is skipped but the ok backend's result appears.
    assert result["aggregate_verdict"] == "supported"
    assert len(result["results"]) == 1
    # The failure should have been logged to stderr.
    captured = capsys.readouterr()
    assert "failing_test_backend" in captured.err


def test_aggregate_verdict_empty_returns_inconclusive():
    """Line 41: empty results returns (inconclusive, 0.0)."""
    verdict, confidence = aggregate_verdict([])
    assert verdict == "inconclusive"
    assert confidence == 0.0


def test_aggregate_verdict_zero_confidence_fallback():
    """Line 57: total_weight==0 falls back to plain average of confidences."""
    # All confidences are 0.0 → total_weight is 0.0 → plain average
    results = [
        _result("supported", 0.0),
        _result("supported", 0.0),
    ]
    verdict, confidence = aggregate_verdict(results)
    assert verdict == "supported"
    assert confidence == 0.0
