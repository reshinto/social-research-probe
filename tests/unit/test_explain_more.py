"""More tests for explanations: clustering, probabilistic, topic_hint, regression branches."""

from __future__ import annotations

import pytest

from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    _baseline_action,
    _purpose_focus,
    explain_bayesian,
    explain_bootstrap,
    explain_huber,
    explain_kaplan_meier,
    explain_kmeans,
    explain_multi_regression,
    explain_naive_bayes,
    explain_pca,
    explain_polynomial,
    explain_regression,
    topic_action_hint,
)


@pytest.mark.parametrize(
    "metric",
    [
        "K-means (k=3) within: 0.5",
        "K-means cluster 0 contains 1/10",
        "K-means cluster 1 contains 6/10",
        "K-means cluster 2 contains 3/10",
        "K-means cluster X bogus",
        "K-means random",
    ],
)
def test_kmeans_branches(metric):
    assert isinstance(explain_kmeans(metric), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("PC1 variance", "top loadings: subscribers=0.9"),
        ("PC1 variance", ""),
        ("PC2 variance", ""),
        ("X", ""),
    ],
)
def test_pca_branches(metric, finding):
    assert isinstance(explain_pca(metric, finding), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("Kaplan-Meier median: 5", "5"),
        ("Kaplan-Meier survival at t=10: 0.6", "0.6"),
        ("Kaplan-Meier other", ""),
    ],
)
def test_km_branches(metric, finding):
    assert isinstance(explain_kaplan_meier(metric, finding), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("Bootstrap CI lower: 0.5", "0.5"),
        ("Bootstrap CI upper: 0.5", "0.5"),
        ("Bootstrap mean of x: 0.5", ""),
        ("Bootstrap unknown", ""),
    ],
)
def test_bootstrap_branches(metric, finding):
    assert isinstance(explain_bootstrap(metric, finding), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Naive Bayes training accuracy: 0.9",
        "Naive Bayes other: 0.5",
        "Naive Bayes accuracy: 0.5",
        "Naive Bayes accuracy: 0.3",
    ],
)
def test_naive_bayes_branches(metric):
    assert isinstance(explain_naive_bayes(metric), str)


@pytest.mark.parametrize(
    "metric,finding",
    [
        ("Bayesian linear coefficient: 0.5", ""),
        ("Bayesian posterior variance: 0.05", ""),
        ("Bayesian unknown", ""),
    ],
)
def test_bayesian_branches(metric, finding):
    assert isinstance(explain_bayesian(metric, finding), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Linear trend slope: 0.05",
        "Linear trend slope: -0.05",
        "Linear trend slope: 0.0",
        "R-squared (goodness of fit): 0.85",
        "R-squared (goodness of fit): 0.5",
        "R-squared (goodness of fit): 0.1",
        "Average period-over-period growth: 0.1",
        "Average period-over-period growth: -0.1",
        "Average period-over-period growth: 0.0",
        "unknown",
    ],
)
def test_regression_branches(metric):
    assert isinstance(explain_regression(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Polynomial (degree 2) R²: 0.85",
        "Polynomial (degree 2) R²: 0.5",
        "Polynomial (degree 3) R²: 0.85",
        "unknown",
    ],
)
def test_polynomial_branches(metric):
    assert isinstance(explain_polynomial(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Huber regression slope: 0.5",
        "Huber regression intercept: 0.0",
        "Huber unknown",
    ],
)
def test_huber_branches(metric):
    assert isinstance(explain_huber(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Multi-regression Adjusted R²: 0.5",
        "Coefficient for trust: 0.3",
        "Intercept for overall: 0.5",
        "unknown",
    ],
)
def test_multi_regression_branches(metric):
    assert isinstance(explain_multi_regression(metric), str)


class TestTopicHint:
    def test_purpose_focus_empty(self):
        assert _purpose_focus([]) == "your goal"

    def test_purpose_focus_known(self):
        assert "fresh angles" in _purpose_focus(["latest-news"])

    def test_purpose_focus_unknown(self):
        assert "career growth" in _purpose_focus(["career_growth"])

    @pytest.mark.parametrize(
        "model",
        [
            "descriptive",
            "spread",
            "regression",
            "growth",
            "outliers",
            "correlation",
            "spearman",
            "mann_whitney",
            "welch_t",
            "polynomial_deg2",
            "polynomial_deg3",
            "kmeans",
            "pca",
            "kaplan_meier",
            "naive_bayes",
            "huber_regression",
            "bayesian_linear",
            "bootstrap",
            "multi_regression",
            "normality",
            "unknown_model",
        ],
    )
    def test_baseline_action(self, model):
        assert isinstance(_baseline_action(model, "ai", "focus"), str)

    def test_action_hint_empty_model(self):
        assert topic_action_hint("", "ai", []) == ""

    def test_action_hint_empty_topic(self):
        assert topic_action_hint("descriptive", "", []) == ""

    def test_action_hint_returns(self):
        assert topic_action_hint("descriptive", "ai", ["latest-news"]) != ""
