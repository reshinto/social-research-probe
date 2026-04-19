"""Tests for social_research_probe.viz.selector.select_and_render.

Uses monkeypatching to verify that the selector delegates to bar.render for
short data and line.render for long data without requiring actual PNG output.
"""

import social_research_probe.viz.bar as bar_mod
import social_research_probe.viz.line as line_mod
from social_research_probe.viz.base import ChartResult
from social_research_probe.viz.selector import select_and_render


def _fake_result(label="fake"):
    """Build a dummy ChartResult for use in monkeypatched renderers."""
    return ChartResult(path="/tmp/fake.png", caption=f"Fake chart: {label}")


def test_short_data_uses_bar_chart(monkeypatch, tmp_path):
    """5 or fewer data points should delegate to bar.render."""
    called_with = {}

    def fake_bar(data, label="values", output_dir=None):
        called_with["renderer"] = "bar"
        called_with["data"] = data
        return _fake_result(label)

    monkeypatch.setattr(bar_mod, "render", fake_bar)

    result = select_and_render([1.0, 2.0, 3.0], label="short", output_dir=str(tmp_path))
    assert called_with.get("renderer") == "bar"
    assert result.path == "/tmp/fake.png"


def test_long_data_uses_line_chart(monkeypatch, tmp_path):
    """6 or more data points should delegate to line.render."""
    called_with = {}

    def fake_line(data, label="values", output_dir=None):
        called_with["renderer"] = "line"
        called_with["data"] = data
        return _fake_result(label)

    monkeypatch.setattr(line_mod, "render", fake_line)

    result = select_and_render(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0], label="long", output_dir=str(tmp_path)
    )
    assert called_with.get("renderer") == "line"
    assert result.path == "/tmp/fake.png"
