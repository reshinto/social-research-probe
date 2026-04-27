"""Topic+purpose-aware action hint appended to stats "what it means" text.

Keeps the layman explanation grounded in the user's actual research so the
table answers not just *what* a stat says but *what to do about it for this
topic and purpose*.
"""

from __future__ import annotations

_PURPOSE_VERBS: dict[str, str] = {
    "latest-news": "fresh angles and recency",
    "latest_news": "fresh angles and recency",
    "trending": "rising momentum",
    "evergreen": "durable value",
    "deep-dive": "depth and authority",
    "deep_dive": "depth and authority",
    "competitive-analysis": "differentiation",
    "competitive_analysis": "differentiation",
    "audience-research": "audience pain points",
    "audience_research": "audience pain points",
}


def _purpose_focus(purposes: list[str]) -> str:
    if not purposes:
        return "your goal"
    parts = [_PURPOSE_VERBS.get(p.lower(), p.replace("_", " ")) for p in purposes]
    return " + ".join(parts)


def _baseline_action(model: str, topic: str, focus: str) -> str:
    if model == "descriptive":
        return (
            f"Use this baseline when judging if a `{topic}` idea clears the bar; lean into {focus}."
        )
    if model == "spread":
        return f"Calibrate how aggressive your `{topic}` differentiation needs to be to stand out on {focus}."
    if model in ("regression", "growth"):
        return f"Treat the trend direction as the prevailing wind for `{topic}`; align {focus} with it or fight it knowingly."
    if model == "outliers":
        return f"Reverse-engineer the outliers — they reveal what `{topic}` audiences reward when {focus} clicks."
    if model in ("correlation", "spearman"):
        return f"If two `{topic}` factors move together, optimising one carries the other; pick the cheaper lever for {focus}."
    if model in ("mann_whitney", "welch_t"):
        return f"A real gap between groups means choose the winning bucket for your `{topic}` `{focus}` push."
    if model in ("polynomial_deg2", "polynomial_deg3"):
        return f"Non-linear curve: there's a sweet-spot length / cadence for `{topic}` — overshooting hurts {focus}."
    if model == "kmeans":
        return f"Distinct clusters mean your `{topic}` audience is segmented; pick one segment and tune {focus} to it."
    if model == "pca":
        return f"The dominant components show what really separates winning `{topic}` content; concentrate {focus} there."
    if model == "kaplan_meier":
        return f"Survival drop-off tells you the half-life of a `{topic}` idea — schedule {focus} before the curve dips."
    if model == "naive_bayes":
        return f"Use the predicted-class odds to pre-screen `{topic}` ideas before investing production effort in {focus}."
    if model == "huber_regression":
        return f"Trend resistant to outliers — trust this slope for `{topic}` planning on {focus}."
    if model == "bayesian_linear":
        return f"Credible intervals let you quote uncertainty when pitching `{topic}` decisions tied to {focus}."
    if model == "bootstrap":
        return f"Confidence interval bounds your worst- and best-case for `{topic}` decisions on {focus}."
    if model == "multi_regression":
        return f"Coefficients rank which `{topic}` levers move the needle most for {focus}."
    if model == "normality":
        return f"Distribution shape decides whether mean or median is the right `{topic}` benchmark for {focus}."
    return ""


def topic_action_hint(model: str, topic: str, purposes: list[str]) -> str:
    """Return one short, action-oriented sentence tying a stat to topic+purpose."""
    if not model or not topic:
        return ""
    return _baseline_action(model, topic, _purpose_focus(purposes))
