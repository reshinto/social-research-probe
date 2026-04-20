"""Dispatch table: maps inferred model names to their explanation functions."""

from __future__ import annotations

from ._common import infer_model
from .clustering import explain_kaplan_meier, explain_kmeans, explain_pca
from .correlation import explain_correlation, explain_outliers, explain_spearman, explain_tests
from .descriptive import explain_descriptive, explain_spread
from .probabilistic import explain_bayesian, explain_bootstrap, explain_naive_bayes
from .regression import (
    explain_huber,
    explain_multi_regression,
    explain_polynomial,
    explain_regression,
)


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
