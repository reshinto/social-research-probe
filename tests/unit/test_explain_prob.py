"""Cover all branches in probabilistic and other explanation modules."""

from __future__ import annotations

import pytest

from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_bayesian,
    explain_bootstrap,
    explain_huber,
    explain_kaplan_meier,
    explain_kmeans,
    explain_naive_bayes,
    explain_pca,
    explain_polynomial,
    explain_regression,
)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("Bootstrap CI lower: 0.5", ""),
        ("Bootstrap CI lower: bogus", ""),
        ("Bootstrap CI upper: 0.5", ""),
        ("Bootstrap CI upper: nope", ""),
        ("Bootstrap mean of x: 0.5", "[0.4, 0.6]"),
        ("Bootstrap mean of x: 0.5", "no range"),
        ("Bootstrap unknown thing", ""),
    ],
)
def test_bootstrap_branches(metric, finding):
    assert isinstance(explain_bootstrap(metric, finding), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Naive Bayes prior P(is_top_n=0): 0.8",
        "Naive Bayes prior P(is_top_n=0): bogus",
        "Naive Bayes prior P(is_top_n=1): 0.2",
        "Naive Bayes prior P(is_top_n=1): 0",
        "Naive Bayes prior P(is_top_n=1): bogus",
        "Naive Bayes training accuracy: 0.95",
        "Naive Bayes training accuracy: 0.8",
        "Naive Bayes training accuracy: 0.5",
        "Naive Bayes training accuracy: bogus",
        "Naive Bayes other: 0.5",
    ],
)
def test_naive_bayes_branches(metric):
    assert isinstance(explain_naive_bayes(metric), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("Bayesian intercept: 0.5 SD 0.05", ""),
        ("Bayesian intercept: missing", ""),
        ("Bayesian residual variance: 0.0001", ""),
        ("Bayesian residual variance: 0.05", ""),
        ("Bayesian residual variance: bogus", ""),
        ("Bayesian coef trust: 0.3 [0.2, 0.4]", ""),
        ("Bayesian coef trend: 0.2 [0.1, 0.3]", ""),
        ("Bayesian coef opportunity: 0.1 [0.05, 0.15]", ""),
        ("Bayesian coef other: 0.5 [0.4, 0.6]", ""),
        ("Bayesian unknown", ""),
    ],
)
def test_bayesian_branches(metric, finding):
    assert isinstance(explain_bayesian(metric, finding), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("Kaplan-Meier median: 5", ""),
        ("Kaplan-Meier median: bogus", ""),
        ("Kaplan-Meier survival at t=10: 0.6", "0.6"),
        ("Kaplan-Meier survival at t=10: bogus", ""),
        ("Kaplan-Meier other", ""),
    ],
)
def test_km_branches(metric, finding):
    assert isinstance(explain_kaplan_meier(metric, finding), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Linear trend slope: 0.05",
        "Linear trend slope: -0.05",
        "Linear trend slope: 0.0001",
        "Linear trend slope: bogus",
        "R-squared (goodness of fit): 0.9",
        "R-squared (goodness of fit): 0.55",
        "R-squared (goodness of fit): 0.25",
        "R-squared (goodness of fit): 0.05",
        "R-squared (goodness of fit): bogus",
        "Average period-over-period growth: 0.5",
        "Average period-over-period growth: -0.5",
        "Average period-over-period growth: 0.001",
        "Average period-over-period growth: bogus",
        "unknown metric",
    ],
)
def test_regression_branches(metric):
    assert isinstance(explain_regression(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Polynomial (degree 2) R²: 0.85",
        "Polynomial (degree 2) R²: 0.4",
        "Polynomial (degree 2) R²: bogus",
        "Polynomial (degree 3) R²: 0.85",
        "Polynomial (degree 3) R²: 0.5",
        "unknown",
    ],
)
def test_polynomial_branches(metric):
    assert isinstance(explain_polynomial(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Huber regression slope: 0.5",
        "Huber regression slope: -0.5",
        "Huber regression slope: 0.0001",
        "Huber regression intercept: 0.5",
        "Huber unknown",
        "Huber regression slope: bogus",
    ],
)
def test_huber_branches(metric):
    assert isinstance(explain_huber(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "K-means (k=3) within: 0.5",
        "K-means cluster A contains 1/10",
        "K-means cluster A contains 6/10",
        "K-means cluster A contains 3/10",
        "K-means cluster broken",
        "K-means random",
    ],
)
def test_kmeans_branches(metric):
    assert isinstance(explain_kmeans(metric), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("PC1 with stuff", "top loadings: subscribers=0.9"),
        ("PC1 alone", ""),
        ("PC2 alone", ""),
        ("Random metric", ""),
    ],
)
def test_pca_branches(metric, finding):
    assert isinstance(explain_pca(metric, finding), str)
