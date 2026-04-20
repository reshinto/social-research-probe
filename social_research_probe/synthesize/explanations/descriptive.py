"""Explanations for descriptive and spread statistics."""

from __future__ import annotations

from ._common import parse_numeric


def explain_descriptive(metric: str) -> str:
    """Mean / median / min / max — sets the competitive baseline for this space."""
    v = parse_numeric(metric)
    if v is None:
        return ""
    if metric.startswith("Mean "):
        if v >= 0.75:
            return f"High baseline ({v:.2f}) — the bar is genuinely high; only well-optimised content will surface here."
        if v >= 0.65:
            return f"Moderate baseline ({v:.2f}) — competitive but accessible; a strong angle can still break through."
        return f"Low baseline ({v:.2f}) — overall quality is weak; even average content has a realistic shot here."
    if metric.startswith("Median "):
        return f"Median {v:.2f} — the true bar to beat; half the competition scores below this."
    if metric.startswith("Min "):
        return f"Floor at {v:.2f} — content scoring below this is unlikely to surface at all."
    if metric.startswith("Max "):
        return f"Ceiling at {v:.2f} — the #1 video sets this benchmark; within 0.05 of this is genuinely top-tier."
    return ""


def explain_spread(metric: str) -> str:
    """Spread metrics — reveals how tightly clustered or differentiated the field is."""
    v = parse_numeric(metric)
    if v is None:
        return ""
    if metric.startswith("Std dev"):
        if v < 0.03:
            return f"Very tight spread ({v:.3f}) — almost every video scores similarly; small improvements in trust or trend shift rank positions significantly."
        if v < 0.06:
            return f"Tight spread ({v:.3f}) — the field is closely matched; incremental improvements in any factor can shift ranking."
        return f"Wide spread ({v:.3f}) — scores vary a lot; strong differentiation on trust or opportunity can leapfrog many competitors."
    if metric.startswith("Interquartile range"):
        if v < 0.05:
            return f"Middle 50% fits within {v:.3f} — very little room to stand out on score alone in the mid-tier."
        return f"Middle 50% spans {v:.3f} — enough spread that positioning matters even in the middle of the market."
    if metric.startswith("Range of"):
        if v > 0.15:
            return f"Wide range of {v:.3f} — clear winners and losers exist; being in the top tier is meaningfully better than being average."
        return f"Narrow range of {v:.3f} — competition is dense; even the best videos are not dramatically ahead."
    if metric.startswith("Skewness"):
        if v < -0.3:
            return f"Left-skewed ({v:.3f}) — a few weak videos pull the average down; the real competition is stronger than averages suggest. Trust median over mean."
        if v > 0.3:
            return f"Right-skewed ({v:.3f}) — a few high performers inflate the average; most videos are weaker than the mean implies. Easier to compete than averages suggest."
        return f"Near-symmetric ({v:.3f}) — no significant outlier distortion; averages are a reliable guide."
    if metric.startswith("Excess kurtosis"):
        if v > 1:
            return f"Fat tails ({v:.3f}) — extreme high and low performers exist more than expected; genuine breakout potential exists here."
        if v < -1:
            return f"Thin tails ({v:.3f}) — almost no one breaks dramatically above average; the market rewards consistency over breakthroughs."
        return f"Normal tails ({v:.3f}) — no unusual concentration at extremes; scores are distributed as expected."
    return ""
