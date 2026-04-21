"""Unit tests for commands/render.py.

Why this file exists:
    Verifies that the render command correctly reads a packet JSON file,
    extracts overall scores, calls stats and viz selectors, and prints a
    structured JSON report. Also checks error handling for missing or invalid
    packet files.

Who calls it:
    pytest during CI and local test runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from social_research_probe.commands import render as render_cmd
from social_research_probe.errors import ValidationError

# ---------------------------------------------------------------------------
# Stub return types
# ---------------------------------------------------------------------------


@dataclass
class _FakeStatResult:
    """Minimal stand-in for stats.base.StatResult used in monkeypatching."""

    name: str
    value: float
    caption: str


@dataclass
class _FakeChartResult:
    """Minimal stand-in for viz.base.ChartResult used in monkeypatching."""

    path: str
    caption: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PACKET = {
    "topic": "AI trends",
    "platform": "youtube",
    "items_top_n": [
        {"title": "A", "scores": {"overall": 0.9}},
        {"title": "B", "scores": {"overall": 0.7}},
    ],
}

_FAKE_STATS = [
    _FakeStatResult(name="mean", value=0.8, caption="Mean overall score: 0.8"),
]
_FAKE_CHART = _FakeChartResult(path="/tmp/chart.png", caption="Bar chart: overall_score")


def _write_packet(tmp_path: Path, data: dict) -> Path:
    """Write a packet dict to a temp JSON file and return its path."""
    p = tmp_path / "packet.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_success_prints_stats_and_chart(monkeypatch, tmp_path, capsys):
    """run() prints a JSON report containing 'stats' and 'chart' keys.

    select_and_run and select_and_render are monkeypatched to avoid real
    file I/O or statistical computation.
    """
    monkeypatch.setattr(render_cmd, "select_and_run", lambda data, label: _FAKE_STATS)
    monkeypatch.setattr(
        render_cmd, "select_and_render", lambda data, label, output_dir: _FAKE_CHART
    )

    packet_path = _write_packet(tmp_path, _PACKET)
    rc = render_cmd.run(str(packet_path))

    assert rc == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert "stats" in report
    assert "chart" in report
    assert report["stats"][0]["name"] == "mean"
    assert report["stats"][0]["value"] == 0.8
    assert report["chart"]["path"] == "/tmp/chart.png"
    assert report["chart"]["caption"] == "Bar chart: overall_score"


def test_run_invalid_json_raises_validation_error(tmp_path):
    """run() raises ValidationError when the packet file is not valid JSON."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    with pytest.raises(ValidationError, match="cannot read packet file"):
        render_cmd.run(str(bad))


def test_run_missing_file_raises_validation_error(tmp_path):
    """run() raises ValidationError when the packet file does not exist."""
    missing = tmp_path / "no_such_file.json"
    with pytest.raises(ValidationError, match="cannot read packet file"):
        render_cmd.run(str(missing))


def test_run_non_dict_packet_raises_validation_error(tmp_path):
    """run() raises ValidationError when the packet JSON is not an object."""
    bad = tmp_path / "list.json"
    bad.write_text("[1, 2, 3]")
    with pytest.raises(ValidationError, match="packet file must contain a JSON object"):
        render_cmd.run(str(bad))
