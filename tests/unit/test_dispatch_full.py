"""Cover all dispatch branches."""

from __future__ import annotations

import pytest

from social_research_probe.services.synthesizing.synthesis.helpers.contextual_explain import (
    contextual_explanation,
)


@pytest.mark.parametrize(
    "metric",
    [
        "Mean overall: 0.5",  # descriptive
        "Std dev x: 0.1",  # spread
        "Linear trend slope: 0.05",  # regression
        "Average period-over-period growth: 0.05",  # growth
        "Outlier fraction: 5",  # outliers
        "Pearson r between a and b: 0.5",  # correlation
        "Spearman rho between a and b: 0.5",  # spearman
        "Mann-Whitney U: 50",  # mann_whitney
        "Welch t-test x vs y: t=2.0, df=5.0, diff=0.5",  # welch_t
        "Normality check x: ok",  # normality
        "Polynomial (degree 2) R²: 0.85",
        "Polynomial (degree 3) R²: 0.85",
        "Bootstrap CI lower: 0.5",
        "Multi-regression R²: 0.99",
        "K-means cluster 1 contains 3/10",
        "PC1 variance",
        "Kaplan-Meier median: 5",
        "Naive Bayes accuracy: 0.9",
        "Huber regression slope: 0.5",
        "Bayesian intercept: 0.5 SD 0.05",
    ],
)
def test_dispatch_each_model(metric):
    assert isinstance(contextual_explanation(metric, ""), str)
