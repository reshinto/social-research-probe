"""Tests for the inline Unicode bar-chart renderer."""

from __future__ import annotations

from social_research_probe.viz.ascii import render_bars


def test_empty_data_returns_placeholder():
    assert render_bars([], label="x") == "x: (no data)"


def test_renders_one_row_per_value():
    out = render_bars([0.5, 1.0], label="score", width=10)
    lines = out.splitlines()
    assert lines[0] == "score (2 items)"
    assert "#1" in lines[1]
    assert "#2" in lines[2]
    assert "0.500" in lines[1]
    assert "1.000" in lines[2]


def test_zero_max_falls_back_to_unit_scale():
    out = render_bars([0.0, 0.0], label="z", width=4)
    lines = out.splitlines()
    assert lines[0] == "z (2 items)"
    assert lines[1].endswith("█")
