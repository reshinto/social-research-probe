"""Focused tests for progress timing logs."""

from __future__ import annotations

import asyncio

from social_research_probe.utils.display.progress import log_with_time


def test_log_with_time_can_emit_input_and_output(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SRP_LOGS", "1")

    @log_with_time("[srp] sample")
    async def sample(data: dict) -> dict:
        return {"items": [{"title": "output", "overall_score": 0.9}]}

    result = asyncio.run(sample({"items": [{"title": "input"}]}))

    assert result == {"items": [{"title": "output", "overall_score": 0.9}]}
    err = capsys.readouterr().err
    assert "[srp] sample input=" in err
    assert "outcome=success" in err
    assert "output=" in err
    assert "input" in err
    assert "output" in err
