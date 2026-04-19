"""Tests for social_research_probe.viz.base.ChartResult.

Verifies that the dataclass is constructed correctly and exposes all
expected fields.
"""

from social_research_probe.viz.base import ChartResult


def test_chart_result_fields():
    """ChartResult stores path and caption without modification."""
    result = ChartResult(path="/tmp/chart.png", caption="Line chart: views over 10 data points")

    assert result.path == "/tmp/chart.png"
    assert result.caption == "Line chart: views over 10 data points"
