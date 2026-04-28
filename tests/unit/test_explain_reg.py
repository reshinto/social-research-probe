"""Cover regression/polynomial/huber/multi explanations branches fully."""

from __future__ import annotations

import pytest

from social_research_probe.services.synthesizing.synthesis.helpers.contextual_models import (
    explain_huber,
    explain_multi_regression,
    explain_polynomial,
    explain_regression,
)


@pytest.mark.parametrize(
    "metric",
    [
        "Linear trend slope: -0.01",
        "Linear trend slope: -0.005",
        "Linear trend slope: 0.001",
        "R-squared (goodness of fit): 0.9",
        "R-squared (goodness of fit): 0.7",
        "R-squared (goodness of fit): 0.4",
        "Average period-over-period growth: -1.0",
        "Average period-over-period growth: 1.0",
        "Average period-over-period growth: 0.0",
        "unknown",
    ],
)
def test_regression_branches(metric):
    assert isinstance(explain_regression(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Polynomial (degree 2) R²: 0.9",
        "Polynomial (degree 2) R²: 0.5",
        "Polynomial (degree 2) leading: -0.001",
        "Polynomial (degree 2) leading: 0.0",
        "Polynomial (degree 3) R²: 0.85",
        "Polynomial (degree 3) leading: 0.001",
        "unknown",
    ],
)
def test_polynomial_branches(metric):
    assert isinstance(explain_polynomial(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Huber intercept: 0.5",
        "Huber slope: -0.05",
        "Huber R²: 0.8",
        "Huber random",
    ],
)
def test_huber_branches(metric):
    assert isinstance(explain_huber(metric), str)


@pytest.mark.parametrize(
    "metric",
    [
        "Intercept for overall: 0.0",
        "Coefficient for trust: 0.45",
        "Coefficient for trust: bogus",
        "Coefficient for trend: 0.30",
        "Coefficient for trend: bogus",
        "Coefficient for opportunity: 0.25",
        "Coefficient for opportunity: bogus",
        "Multi-regression R²: 0.999",
        "Multi-regression R²: 0.9",
        "Multi-regression R²: bogus",
        "Adjusted R²: 0.85",
        "Adjusted R²: bogus",
        "unknown",
    ],
)
def test_multi_regression_branches(metric):
    assert isinstance(explain_multi_regression(metric), str)
