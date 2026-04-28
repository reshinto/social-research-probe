"""Tests for synthesizing.explanations modules."""

from __future__ import annotations

import pytest

from social_research_probe.services.synthesizing.synthesis.helpers.contextual_explain import (
    contextual_explanation,
    infer_model,
    parse_numeric,
)
from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_bayesian,
    explain_bootstrap,
    explain_correlation,
    explain_descriptive,
    explain_huber,
    explain_kaplan_meier,
    explain_kmeans,
    explain_multi_regression,
    explain_naive_bayes,
    explain_outliers,
    explain_pca,
    explain_polynomial,
    explain_regression,
    explain_spearman,
    explain_spread,
    explain_tests,
)


class TestCommon:
    def test_infer_model_descriptive(self):
        assert infer_model("Mean overall: 0.5") == "descriptive"

    def test_infer_model_spread(self):
        assert infer_model("Std dev x: 0.1") == "spread"

    def test_infer_model_correlation(self):
        assert infer_model("Pearson r between a and b: 0.3") == "correlation"

    def test_infer_model_unknown(self):
        assert infer_model("blah") == ""

    def test_parse_numeric_basic(self):
        assert parse_numeric("foo: 0.42") == 0.42
        assert parse_numeric("x: -1.5") == -1.5
        assert parse_numeric("no num") is None


@pytest.mark.parametrize(
    "metric",
    [
        "Mean overall: 0.80",
        "Mean overall: 0.70",
        "Mean overall: 0.50",
        "Median overall: 0.60",
        "Min overall: 0.20",
        "Max overall: 0.95",
        "Mean overall: bogus",
    ],
)
def test_descriptive_branches(metric):
    out = explain_descriptive(metric)
    assert isinstance(out, str)


@pytest.mark.parametrize(
    "metric",
    [
        "Std dev x: 0.02",
        "Std dev x: 0.04",
        "Std dev x: 0.10",
        "Interquartile range: 0.03",
        "Interquartile range: 0.10",
        "Range of x: 0.20",
        "Range of x: 0.05",
        "Skewness x: -0.5",
        "Skewness x: 0.5",
        "Skewness x: 0.0",
        "Excess kurtosis x: 1.5",
        "Excess kurtosis x: -1.5",
        "Excess kurtosis x: 0.0",
        "Std dev x: bogus",
    ],
)
def test_spread_branches(metric):
    out = explain_spread(metric)
    assert isinstance(out, str)


@pytest.mark.parametrize(
    "metric",
    [
        "Pearson r between trust and trend: -0.6",
        "Pearson r between trust and trend: -0.3",
        "Pearson r between trust and trend: 0.6",
        "Pearson r between trust and trend: 0.3",
        "Pearson r between trust and trend: 0.05",
        "Pearson r: bogus",
    ],
)
def test_correlation_branches(metric):
    out = explain_correlation(metric)
    assert isinstance(out, str)


@pytest.mark.parametrize(
    "metric",
    [
        "Spearman rho between a and b: 0.6",
        "Spearman rho between a and b: 0.1",
        "Spearman: bogus",
    ],
)
def test_spearman_branches(metric):
    out = explain_spearman(metric)
    assert isinstance(out, str)


@pytest.mark.parametrize(
    "metric",
    [
        "Outliers in x: 0 of 10",
        "Outliers in x: 1 of 10",
        "Outliers in x: 5 of 10",
        "Outliers in x: bogus",
        "Outlier fraction: 0",
        "Outlier fraction: 5",
        "Outlier fraction: 50",
        "Outlier fraction: bogus",
    ],
)
def test_outliers_branches(metric):
    out = explain_outliers(metric)
    assert isinstance(out, str)


@pytest.mark.parametrize(
    "metric",
    [
        "Mann-Whitney U: 50",
        "Welch t-test x vs y: t=2.0, df=5.0, diff=0.5",
        "Welch t-test x vs y: nodiff",
        "Normality check x: ok",
    ],
)
def test_tests_branches(metric):
    out = explain_tests(metric, "")
    assert isinstance(out, str)


def test_contextual_explanation_descriptive():
    assert contextual_explanation("Mean overall: 0.5", "0.5") != ""


def test_contextual_explanation_unknown():
    assert contextual_explanation("nothing", "") == ""


@pytest.mark.parametrize(
    "fn,metric",
    [
        (explain_regression, "Linear trend slope: 0.05"),
        (explain_regression, "R-squared (goodness of fit): 0.6"),
        (explain_regression, "Average period-over-period growth: 0.05"),
        (explain_polynomial, "Polynomial (degree 2): 0.5"),
        (explain_polynomial, "Polynomial (degree 3): 0.5"),
        (explain_huber, "Huber regression slope: 0.5"),
        (explain_multi_regression, "Multi-regression: 0.5"),
        (explain_multi_regression, "Coefficient for trust: 0.3"),
        (explain_bootstrap, "Bootstrap CI lower: 0.5"),
        (explain_bootstrap, "Bootstrap mean of x: 0.5"),
        (explain_naive_bayes, "Naive Bayes accuracy: 0.8"),
        (explain_bayesian, "Bayesian linear coefficient: 0.5"),
        (explain_kmeans, "K-means clusters: 3"),
        (explain_pca, "PC1 variance ratio: 0.5"),
        (explain_pca, "PC2 variance ratio: 0.3"),
        (explain_kaplan_meier, "Kaplan-Meier median: 5"),
    ],
)
def test_other_explanation_helpers(fn, metric):
    out = fn(metric, "") if fn.__code__.co_argcount == 2 else fn(metric)
    assert isinstance(out, str)
