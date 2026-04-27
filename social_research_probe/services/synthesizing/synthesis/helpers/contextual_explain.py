"""Dispatch and common utilities for per-model statistical explanations."""

from __future__ import annotations

import re

from .contextual_models import (
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

# Maps metric string prefixes to the statistical model that produced them.
# Order matters: more specific prefixes must appear before shorter ones.
_MODEL_PREFIXES: list[tuple[str, str]] = [
    ("Mean ", "descriptive"),
    ("Median ", "descriptive"),
    ("Min ", "descriptive"),
    ("Max ", "descriptive"),
    ("Skewness", "spread"),
    ("Excess kurtosis", "spread"),
    ("Std dev", "spread"),
    ("Interquartile range", "spread"),
    ("Range of", "spread"),
    ("Linear trend slope", "regression"),
    ("R-squared (goodness of fit)", "regression"),
    ("Average period-over-period growth", "growth"),
    ("Outlier fraction", "outliers"),
    ("Outliers in", "outliers"),
    ("Pearson r", "correlation"),
    ("Spearman", "spearman"),
    ("Mann-Whitney", "mann_whitney"),
    ("Welch t-test", "welch_t"),
    ("Normality check", "normality"),
    ("Polynomial (degree 2)", "polynomial_deg2"),
    ("Polynomial (degree 3)", "polynomial_deg3"),
    ("Bootstrap CI", "bootstrap"),
    ("Bootstrap mean", "bootstrap"),
    ("Multi-regression", "multi_regression"),
    ("Adjusted R²", "multi_regression"),
    ("Intercept for overall", "multi_regression"),
    ("Coefficient for", "multi_regression"),
    ("K-means", "kmeans"),
    ("PC1 ", "pca"),
    ("PC2 ", "pca"),
    ("Kaplan-Meier", "kaplan_meier"),
    ("Naive Bayes", "naive_bayes"),
    ("Huber ", "huber_regression"),
    ("Bayesian ", "bayesian_linear"),
]


def infer_model(metric: str) -> str:
    """Return the model name for a metric string, or empty string if unknown."""
    for prefix, model in _MODEL_PREFIXES:
        if metric.startswith(prefix):
            return model
    return ""


def parse_numeric(s: str) -> float | None:
    """Extract the first numeric value that appears after a colon in s."""
    m = re.search(r":\s*(-?\d+\.?\d*)", s)
    return float(m.group(1)) if m else None


def contextual_explanation(metric: str, finding: str) -> str:
    """Return a plain-English, decision-relevant sentence for one highlight row.

    Dispatches to the model-specific explanation function based on the metric
    prefix. Returns an empty string when no explanation is available.
    """
    model = infer_model(metric)
    if model == "descriptive":
        return explain_descriptive(metric)
    if model == "spread":
        return explain_spread(metric)
    if model in ("regression", "growth"):
        return explain_regression(metric)
    if model == "outliers":
        return explain_outliers(metric)
    if model == "correlation":
        return explain_correlation(metric)
    if model == "spearman":
        return explain_spearman(metric)
    if model in ("mann_whitney", "welch_t", "normality"):
        return explain_tests(metric, finding)
    if model in ("polynomial_deg2", "polynomial_deg3"):
        return explain_polynomial(metric)
    if model == "bootstrap":
        return explain_bootstrap(metric, finding)
    if model == "multi_regression":
        return explain_multi_regression(metric)
    if model == "kmeans":
        return explain_kmeans(metric)
    if model == "pca":
        return explain_pca(metric, finding)
    if model == "kaplan_meier":
        return explain_kaplan_meier(metric, finding)
    if model == "naive_bayes":
        return explain_naive_bayes(metric)
    if model == "huber_regression":
        return explain_huber(metric)
    if model == "bayesian_linear":
        return explain_bayesian(metric, finding)
    return ""
