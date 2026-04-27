"""Per-model explanation helpers for statistical highlights."""

from __future__ import annotations

from ._common import infer_model
from ._dispatch import contextual_explanation
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

__all__ = [
    "contextual_explanation",
    "explain_bayesian",
    "explain_bootstrap",
    "explain_correlation",
    "explain_descriptive",
    "explain_huber",
    "explain_kaplan_meier",
    "explain_kmeans",
    "explain_multi_regression",
    "explain_naive_bayes",
    "explain_outliers",
    "explain_pca",
    "explain_polynomial",
    "explain_regression",
    "explain_spearman",
    "explain_spread",
    "explain_tests",
    "infer_model",
]
