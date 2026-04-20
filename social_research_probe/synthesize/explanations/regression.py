"""Explanations for regression, polynomial, and Huber models."""

from __future__ import annotations

from ._common import parse_numeric


def explain_regression(metric: str) -> str:
    """Regression / growth — reveals quality drop-off and whether rankings are locking in."""
    v = parse_numeric(metric)
    if v is None:
        return ""
    if metric.startswith("Linear trend slope"):
        if v < -0.008:
            return f"Steep drop-off ({v:.4f}/rank) — only the top 3-5 videos dominate; ranking position matters enormously and the mid-tier is a dead zone."
        if v < -0.003:
            return f"Gradual drop-off ({v:.4f}/rank) — quality declines consistently but many videos are still competitive; no single dominant player locks out the space."
        return f"Flat trend ({v:.4f}/rank) — scores barely decline by rank; content quality is very uniform and ranking is harder to predict."
    if metric.startswith("R-squared (goodness of fit)"):
        if v >= 0.85:
            return f"Strong fit ({v:.2f}) — rankings follow a clear, predictable hierarchy with little random noise; quality consistently determines position."
        if v >= 0.6:
            return f"Moderate fit ({v:.2f}) — rankings have some pattern but also noise; a few unexpected videos are disrupting the expected order."
        return f"Weak fit ({v:.2f}) — rankings are somewhat random; the algorithm may be surfacing content for reasons not captured in these scores."
    if metric.startswith("Average period-over-period growth"):
        if v < -0.5:
            return f"Rankings are locking in ({v:.2f}%/step) — top positions are stabilising and harder to displace; entering later means fighting established content."
        if v > 0.5:
            return f"Rankings still in flux ({v:.2f}%/step) — the space is unsettled; an early strong entry can still claim top position."
        return f"Rankings are stable ({v:.2f}%/step) — the hierarchy is settled; displacing top content requires a significantly better approach."
    return ""


def explain_polynomial(metric: str) -> str:
    """Polynomial fits — checks whether the quality drop-off accelerates or has an S-curve shape."""
    v = parse_numeric(metric)
    if v is None:
        return ""
    if metric.startswith("Polynomial (degree 2) R²"):
        if v > 0.85:
            return f"Curved fit at {v:.0%} — the score drop-off accelerates; the top videos pull increasingly further ahead as you go deeper."
        return f"Curved fit at {v:.0%} — slight acceleration, but mostly linear; the field declines fairly evenly."
    if metric.startswith("Polynomial (degree 2) leading"):
        if v < -0.0002:
            return f"Steep curve ({v:.5f}) — quality drops sharply after the top tier; mid-tier videos are significantly weaker and not worth targeting."
        return f"Shallow curve ({v:.5f}) — the acceleration in quality drop-off is minor; the field declines fairly linearly."
    if metric.startswith("Polynomial (degree 3) R²"):
        return f"Best-fit curve at {v:.0%} — most reliable polynomial model; confirms the overall trend shape."
    if metric.startswith("Polynomial (degree 3) leading"):
        return f"Minor S-curve adjustment ({v:.5f}) — the main trend is linear with a small non-linear correction at the extremes."
    return ""


def explain_huber(metric: str) -> str:
    """Huber regression — outlier-resistant trend line confirming the ranking decay is real."""
    v = parse_numeric(metric)
    if v is None:
        return ""
    if metric.startswith("Huber intercept"):
        return f"Reliable baseline at {v:.3f} — confirmed even with outliers removed; the average is not being distorted by unusual videos."
    if metric.startswith("Huber slope"):
        return f"Score drops {abs(v):.4f} per rank even without outlier influence — the gradual decline is real, not an artifact of unusual videos."
    if metric.startswith("Huber R²"):
        return f"Outlier-resistant fit at {v:.0%} — close to the standard regression, confirming outliers have limited impact on the overall trend."
    return ""


def explain_multi_regression(metric: str) -> str:
    """Multi-regression — reveals the exact weight of each scoring factor."""
    v = parse_numeric(metric)
    if metric.startswith("Intercept for overall"):
        return "Formula offset — use alongside the coefficients below to understand exactly how the overall score is calculated."
    if metric.startswith("Coefficient for trust"):
        return (
            f"Trust is weighted at {v:.0%} of overall score — the largest single lever. Improving source credibility has the biggest measurable impact on ranking."
            if v is not None
            else ""
        )
    if metric.startswith("Coefficient for trend"):
        return (
            f"Trend is weighted at {v:.0%} of overall score — second largest lever. Riding a current trend is worth about two-thirds as much as improving trust."
            if v is not None
            else ""
        )
    if metric.startswith("Coefficient for opportunity"):
        return (
            f"Opportunity is weighted at {v:.0%} of overall score — smallest lever, but still meaningful. Targeting a niche angle adds value at the margin."
            if v is not None
            else ""
        )
    if metric.startswith("Multi-regression R²") or metric.startswith("Adjusted R²"):
        if v and v >= 0.999:
            return "Perfect fit — the overall score is a deterministic formula of trust, trend, and opportunity. No hidden factors are at play."
        return (
            f"Formula explains {v:.0%} of variance — nearly complete; a small residual remains outside the model."
            if v
            else ""
        )
    return ""
