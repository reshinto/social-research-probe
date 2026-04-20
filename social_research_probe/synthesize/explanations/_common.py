"""Shared utilities for the per-model explanation helpers."""

from __future__ import annotations

import re

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
