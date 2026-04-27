"""Tests for synthesizing pure helpers: divergence, explain, llm_contract."""

from __future__ import annotations

import pytest

from social_research_probe.services.synthesizing import explain, llm_contract
from social_research_probe.technologies.statistics.base import StatResult
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.text import divergence


class TestDivergence:
    def test_both_empty(self):
        assert divergence.jaccard_divergence("", "") == 0.0

    def test_identical(self):
        assert divergence.jaccard_divergence("hello world", "WORLD hello") == 0.0

    def test_disjoint(self):
        assert divergence.jaccard_divergence("a b c", "x y z") == 1.0

    def test_partial(self):
        d = divergence.jaccard_divergence("a b c", "b c d")
        assert 0.0 < d < 1.0


class TestExplain:
    def test_unknown_returns_caption(self):
        sr = StatResult(name="other", value=1.0, caption="cap")
        assert explain.explain(sr) == "cap"

    def test_growth_flat(self):
        sr = StatResult(name="growth_rate", value=0.001, caption="cap")
        assert "flat" in explain.explain(sr)

    def test_growth_rising(self):
        sr = StatResult(name="growth_rate", value=0.5, caption="cap")
        assert "rising" in explain.explain(sr)

    def test_growth_falling(self):
        sr = StatResult(name="growth_rate", value=-0.5, caption="cap")
        assert "falling" in explain.explain(sr)

    def test_slope_no_trend(self):
        sr = StatResult(name="slope", value=0.0001, caption="cap")
        assert "no meaningful linear trend" in explain.explain(sr)

    def test_slope_increases(self):
        sr = StatResult(name="slope", value=0.5, caption="cap")
        assert "increases" in explain.explain(sr)

    def test_r_squared_levels(self):
        for v, expect in [(0.9, "strong"), (0.6, "moderate"), (0.3, "weak"), (0.05, "no real")]:
            sr = StatResult(name="r_squared", value=v, caption="cap")
            assert expect in explain.explain(sr)

    def test_pearson_levels(self):
        for v in (0.05, 0.2, 0.5, 0.8, -0.8):
            sr = StatResult(name="pearson_r", value=v, caption="cap")
            assert "—" in explain.explain(sr) or "correlation" in explain.explain(sr)

    def test_outlier_count_zero(self):
        sr = StatResult(name="outlier_count", value=0.0, caption="cap")
        assert "no extreme" in explain.explain(sr)

    def test_outlier_count_some(self):
        sr = StatResult(name="outlier_count", value=3.0, caption="cap")
        assert "3" in explain.explain(sr)

    def test_outlier_fraction(self):
        sr = StatResult(name="outlier_fraction", value=0.0, caption="cap")
        assert "well-behaved" in explain.explain(sr)
        sr2 = StatResult(name="outlier_fraction", value=0.2, caption="cap")
        assert "20%" in explain.explain(sr2)

    def test_iqr_and_range(self):
        for n in ("iqr", "range"):
            sr = StatResult(name=n, value=1.0, caption="cap")
            out = explain.explain(sr)
            assert "—" in out

    def test_stdev_levels(self):
        for v in (0.01, 0.1, 1.0):
            sr = StatResult(name="stdev_x", value=v, caption="cap")
            assert "—" in explain.explain(sr)

    def test_mean_median(self):
        for n in ("mean_x", "median_x"):
            sr = StatResult(name=n, value=1.0, caption="cap")
            assert "—" in explain.explain(sr)


class TestLlmContract:
    def test_parse_valid(self):
        out = llm_contract.parse_synthesis_response(
            {"compiled_synthesis": "a", "opportunity_analysis": "b", "report_summary": "c"}
        )
        assert out["compiled_synthesis"] == "a"

    def test_parse_missing_key(self):
        with pytest.raises(ValidationError):
            llm_contract.parse_synthesis_response({"compiled_synthesis": "a"})

    def test_parse_non_string(self):
        with pytest.raises(ValidationError):
            llm_contract.parse_synthesis_response(
                {"compiled_synthesis": 1, "opportunity_analysis": "b", "report_summary": "c"}
            )
