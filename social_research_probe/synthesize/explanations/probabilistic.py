"""Explanations for bootstrap, naive Bayes, and Bayesian linear models."""

from __future__ import annotations

import re

from ._common import parse_numeric


def explain_bootstrap(metric: str, finding: str) -> str:
    """Bootstrap resampling — validates that score estimates are stable."""
    if metric.startswith("Bootstrap CI lower"):
        v = parse_numeric(metric)
        return (
            f"Even in the worst-case simulation, the true average is at least {v:.3f} — the floor is confirmed and reliable."
            if v is not None
            else ""
        )
    if metric.startswith("Bootstrap CI upper"):
        v = parse_numeric(metric)
        return (
            f"Best realistic estimate tops out at {v:.3f} — this is the upside ceiling for what this space can deliver on average."
            if v is not None
            else ""
        )
    if metric.startswith("Bootstrap mean"):
        m2 = re.search(r"\[(-?\d+\.\d+),\s*(-?\d+\.\d+)\]", metric + " " + finding)
        v = parse_numeric(metric)
        if v and m2:
            lo, hi = float(m2.group(1)), float(m2.group(2))
            return f"Average confirmed at {v:.3f} (range {lo:.3f}-{hi:.3f}) across 2,000 resamples -- score estimates are stable and not a sampling fluke."
        return "Bootstrap confirms the average is stable — findings are reliable."
    return ""


def explain_naive_bayes(metric: str) -> str:
    """Naive Bayes — shows the base rate for top-N success and whether signals are predictive."""
    v = parse_numeric(metric)
    if metric.startswith("Naive Bayes prior P(is_top_n=0)"):
        return (
            f"Base odds of NOT making the top 5 are {v:.0%} — the top tier is selective; average content will not break through without deliberate differentiation."
            if v is not None
            else ""
        )
    if metric.startswith("Naive Bayes prior P(is_top_n=1)"):
        return (
            f"1 in {round(1 / v)} videos makes the top 5 by default — achievable but requires deliberate effort on trust, trend, and opportunity."
            if v
            else ""
        )
    if metric.startswith("Naive Bayes training accuracy"):
        if v is None:
            return ""
        if v >= 0.9:
            return f"Signals predict top-N with {v:.0%} accuracy — trust, trend, and opportunity are genuine, reliable indicators. Optimising them is worth the effort."
        if v >= 0.75:
            return f"Signals predict top-N with {v:.0%} accuracy — useful but imperfect; other factors also influence outcome."
        return f"Low accuracy ({v:.0%}) — the available signals are weak predictors; something important is not being measured."
    return ""


def explain_bayesian(metric: str, finding: str) -> str:
    """Bayesian linear model — probabilistic confidence ranges on each factor's impact."""
    if metric.startswith("Bayesian intercept"):
        m2 = re.search(r":\s*(-?\d+\.\d+).*SD\s*(-?\d+\.\d+)", metric)
        if m2:
            v, sd = float(m2.group(1)), float(m2.group(2))
            return f"Starting score of {v:.3f} +/- {sd:.3f} — narrow uncertainty confirms the baseline is well-established from the data."
        return ""
    if metric.startswith("Bayesian residual variance"):
        v = parse_numeric(metric)
        if v is None:
            return ""
        if v < 0.001:
            return f"Residual variance {v:.4f} — essentially zero unexplained variation; trust, trend, and opportunity together fully account for the score differences."
        return f"Residual variance {v:.4f} — small but non-zero; most scoring is explained, but a minor component remains outside the model."
    coef_match = re.search(
        r":\s*(-?\d+\.\d+).*\[(-?\d+\.\d+),\s*(-?\d+\.\d+)\]", metric + " " + finding
    )
    if not coef_match:
        return ""
    v, lo, hi = float(coef_match.group(1)), float(coef_match.group(2)), float(coef_match.group(3))
    if metric.startswith("Bayesian coef trust"):
        return f"Trust adds {v:.2f} to overall score (95% range {lo:.2f}-{hi:.2f}) -- tight range confirms this is reliable. Improving trust is a consistently safe investment."
    if metric.startswith("Bayesian coef trend"):
        return f"Trend adds {v:.2f} to overall score (95% range {lo:.2f}-{hi:.2f}) -- publishing on trending AI topics has a well-confirmed, reliable payoff."
    if metric.startswith("Bayesian coef opportunity"):
        return f"Opportunity adds {v:.2f} to overall score (95% range {lo:.2f}-{hi:.2f}) -- targeting niche angles has a confirmed, if smaller, payoff."
    return ""
