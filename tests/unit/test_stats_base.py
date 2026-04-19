"""Tests for social_research_probe.stats.base.StatResult.

Verifies that the dataclass is constructed correctly and exposes all
expected fields with the right types.
"""

from social_research_probe.stats.base import StatResult


def test_stat_result_fields():
    """StatResult stores name, value, and caption without modification."""
    result = StatResult(name="mean_views", value=42.5, caption="Average views: 42.5")

    assert result.name == "mean_views"
    assert result.value == 42.5
    assert result.caption == "Average views: 42.5"
