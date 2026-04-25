"""Unit tests for commands/corroborate_claims.py.

Why this file exists:
    Verifies that the corroborate-claims command correctly reads a claims JSON
    file, builds Claim objects, calls corroborate_claim for each, and writes
    results either to stdout or an output file. Also checks error handling for
    bad input files.

Who calls it:
    pytest during CI and local test runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from social_research_probe.errors import ValidationError

from social_research_probe.commands import corroborate_claims as cc_cmd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_VERDICT = {"verdict": "supported", "confidence": 0.9, "reasoning": "ok"}

_CLAIMS_DATA = {
    "claims": [
        {"text": "The sky is blue because of Rayleigh scattering.", "source_text": "Physics 101"},
        {"text": "Water boils at 100°C at sea level."},
    ]
}


def _write_claims(tmp_path: Path, data: dict) -> Path:
    """Write a claims dict to a temp JSON file and return the path."""
    p = tmp_path / "claims.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_success_stdout(monkeypatch, tmp_path, capsys):
    """run() writes a JSON object with 'results' list to stdout.

    corroborate_claim is monkeypatched so no real network calls happen.
    """
    calls = []

    async def fake_corroborate(claim, backends):
        calls.append((claim.text, backends))
        return _FAKE_VERDICT

    monkeypatch.setattr(cc_cmd, "corroborate_claim", fake_corroborate)

    input_path = _write_claims(tmp_path, _CLAIMS_DATA)
    rc = cc_cmd.run(str(input_path), backends=["exa", "llm_search"])

    assert rc == 0
    captured = capsys.readouterr()
    out = json.loads(captured.out)
    assert "results" in out
    assert len(out["results"]) == 2
    assert out["results"][0] == _FAKE_VERDICT
    # Verify each claim was dispatched with the right backends.
    assert all(b == ["exa", "llm_search"] for _, b in calls)


def test_run_with_output_file(monkeypatch, tmp_path):
    """run() writes the JSON results to output_path when provided."""
    monkeypatch.setattr(cc_cmd, "corroborate_claim", AsyncMock(return_value=_FAKE_VERDICT))

    input_path = _write_claims(tmp_path, _CLAIMS_DATA)
    output_path = tmp_path / "out.json"

    rc = cc_cmd.run(str(input_path), backends=["llm_search"], output_path=str(output_path))

    assert rc == 0
    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert "results" in data
    assert len(data["results"]) == 2


def test_run_invalid_json_raises_validation_error(tmp_path):
    """run() raises ValidationError when the input file contains invalid JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json at all {{{")
    with pytest.raises(ValidationError, match="cannot read claims file"):
        cc_cmd.run(str(bad_file), backends=["llm_search"])


def test_run_missing_file_raises_validation_error(tmp_path):
    """run() raises ValidationError when the input file does not exist."""
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(ValidationError, match="cannot read claims file"):
        cc_cmd.run(str(missing), backends=["llm_search"])


def test_run_raises_when_corroboration_service_disabled(monkeypatch, tmp_path):
    input_path = _write_claims(tmp_path, _CLAIMS_DATA)
    monkeypatch.setattr(
        cc_cmd,
        "load_active_config",
        lambda: type(
            "Cfg",
            (),
            {
                "stage_enabled": staticmethod(lambda platform, name: True),
                "service_enabled": staticmethod(lambda name: name != "corroboration"),
            },
        )(),
    )
    with pytest.raises(ValidationError, match=r"services\.corroboration is false"):
        cc_cmd.run(str(input_path), backends=["llm_search"])


