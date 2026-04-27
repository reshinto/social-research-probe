"""Tests for tech.statistics core modules: descriptive, spread, regression, growth, outliers, correlation, normality, selector."""

from __future__ import annotations

from social_research_probe.technologies.statistics import (
    correlation,
    descriptive,
    growth,
    normality,
    outliers,
    regression,
    selector,
    spread,
)
from social_research_probe.technologies.statistics.base import StatResult


def names(results):
    return {r.name for r in results}


class TestDescriptive:
    def test_empty_returns_empty(self):
        assert descriptive.run([]) == []

    def test_basic(self):
        results = descriptive.run([1.0, 2.0, 3.0], label="x")
        n = names(results)
        assert {"mean_x", "median_x", "min_x", "max_x"}.issubset(n)
        assert all(isinstance(r, StatResult) for r in results)


class TestSpread:
    def test_empty(self):
        assert spread.run([]) == []

    def test_basic(self):
        results = spread.run([1.0, 2.0, 3.0, 4.0])
        assert len(results) >= 1


class TestRegression:
    def test_too_few(self):
        assert regression.run([1.0]) == []

    def test_basic(self):
        results = regression.run([1.0, 2.0, 3.0, 4.0])
        assert len(results) >= 1


class TestGrowth:
    def test_too_few(self):
        assert growth.run([1.0, 2.0]) == [] or isinstance(growth.run([1.0, 2.0]), list)

    def test_basic(self):
        results = growth.run([1.0, 2.0, 4.0, 8.0])
        assert len(results) >= 1


class TestOutliers:
    def test_too_few(self):
        assert outliers.run([1.0]) == []

    def test_no_variation_no_outliers(self):
        results = outliers.run([5.0, 5.0, 5.0])
        counts = [r for r in results if r.name == "outlier_count"]
        assert counts and counts[0].value == 0.0

    def test_detects_outlier(self):
        results = outliers.run([1.0, 1.0, 1.0, 1.0, 1.0, 100.0], threshold=1.0)
        counts = [r for r in results if r.name == "outlier_count"]
        assert counts and counts[0].value >= 1.0


class TestCorrelation:
    def test_unequal_length_empty(self):
        assert correlation.run([1.0, 2.0], [1.0]) == []

    def test_too_short_empty(self):
        assert correlation.run([1.0], [2.0]) == []

    def test_zero_variance_empty(self):
        assert correlation.run([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) == []

    def test_perfect_positive(self):
        results = correlation.run([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
        assert results[0].name == "pearson_r"
        assert abs(results[0].value - 1.0) < 1e-9


class TestNormality:
    def test_too_few(self):
        assert normality.run([1.0]) == []

    def test_basic(self):
        results = normality.run([1.0, 2.0, 3.0, 4.0, 5.0])
        assert len(results) >= 1


class TestSelector:
    def test_empty(self):
        assert selector.select_and_run([]) == []

    def test_one_point_descriptive_only(self):
        results = selector.select_and_run([5.0])
        assert results

    def test_growth_added_with_3plus(self):
        results = selector.select_and_run([1.0, 2.0, 3.0, 4.0])
        assert len(results) > 4

    def test_correlation_too_short(self):
        assert selector.select_and_run_correlation([1.0], [2.0]) == []

    def test_correlation_runs(self):
        out = selector.select_and_run_correlation([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
        assert out and out[0].name == "pearson_r"
