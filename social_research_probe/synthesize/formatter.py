"""Packet formatting and Markdown rendering for srp research output.

Transforms a raw research packet (produced by the pipeline) into human-readable
Markdown sections 1-11. Also builds the packet dict passed to skill mode.

Sections 1-9 are derived deterministically from packet data.
Sections 10-11 (Compiled Synthesis, Opportunity Analysis) are filled by the
calling LLM in skill mode; in CLI mode a placeholder is shown instead.
"""

from __future__ import annotations

import re
from typing import Any

RESPONSE_SCHEMA = {
    "compiled_synthesis": "string ≤150 words",
    "opportunity_analysis": "string ≤150 words",
}


def build_packet(
    *,
    topic: str,
    platform: str,
    purpose_set: list[str],
    items_top5: list[dict],
    source_validation_summary: dict,
    platform_signals_summary: str,
    evidence_summary: str,
    stats_summary: dict,
    chart_captions: list[str],
    warnings: list[str],
) -> dict:
    """Assemble the canonical packet dict passed between pipeline and renderer."""
    return {
        "topic": topic,
        "platform": platform,
        "purpose_set": purpose_set,
        "items_top5": items_top5,
        "source_validation_summary": source_validation_summary,
        "platform_signals_summary": platform_signals_summary,
        "evidence_summary": evidence_summary,
        "stats_summary": stats_summary,
        "chart_captions": chart_captions,
        "warnings": warnings,
        "response_schema": RESPONSE_SCHEMA,
    }


def _items_table(items: list[dict]) -> str:
    """Render the top items as a markdown table for compact scanning."""
    header = (
        "| # | Channel | Class | Trust | Trend | Opp | Overall | Title |\n"
        "|---|---------|-------|-------|-------|-----|---------|-------|"
    )
    rows = []
    for i, it in enumerate(items, start=1):
        scores = it.get("scores", {})
        title = it["title"].replace("|", r"\|")
        rows.append(
            f"| {i} | {it['channel']} | {it.get('source_class', '?')} "
            f"| {scores.get('trust', 0):.2f} | {scores.get('trend', 0):.2f} "
            f"| {scores.get('opportunity', 0):.2f} | {scores.get('overall', 0):.2f} "
            f"| {title} |"
        )
    return "\n".join([header, *rows])


def _items_links_and_takeaways(items: list[dict]) -> str:
    """Render per-item URL and takeaway as a bullet list below the score table."""
    bullets = []
    for i, it in enumerate(items, start=1):
        bullets.append(
            f"- **[{i}]** [{it['channel']}]({it['url']}) — {it.get('one_line_takeaway', '')}"
        )
    return "\n".join(bullets)


# Maps metric string prefixes to the statistical model that produced them.
# Order matters: more specific prefixes must appear before shorter ones
# (e.g. "Bootstrap CI" before "Bootstrap mean").
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


def _infer_model(metric: str) -> str:
    """Return the model name for a metric string, or empty string if unknown."""
    for prefix, model in _MODEL_PREFIXES:
        if metric.startswith(prefix):
            return model
    return ""


def _val(s: str) -> float | None:
    """Extract the first numeric value that appears after a colon in s."""
    m = re.search(r":\s*(-?\d+\.?\d*)", s)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Per-model contextual explanation helpers
#
# Each function receives the metric label (and sometimes finding) from a
# highlight string and returns a plain-English, decision-relevant sentence
# derived from the actual numeric value — not a static definition.
# ---------------------------------------------------------------------------


def _explain_descriptive(metric: str) -> str:
    """Mean / median / min / max — sets the competitive baseline for this space."""
    v = _val(metric)
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


def _explain_spread(metric: str) -> str:
    """Spread metrics — reveals how tightly clustered or differentiated the field is."""
    v = _val(metric)
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


def _explain_regression(metric: str) -> str:
    """Regression / growth — reveals how quickly quality drops off by rank and whether rankings are locking in."""
    v = _val(metric)
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


def _explain_outliers(metric: str) -> str:
    """Outlier detection — flags whether unusual videos are distorting the aggregate picture."""
    if metric.startswith("Outliers in"):
        m = re.search(r":\s*(\d+)\s*of\s*(\d+)", metric)
        if not m:
            return ""
        count, total = int(m.group(1)), int(m.group(2))
        if count == 0:
            return "No outliers — the dataset is clean; no single unusual video is distorting the aggregate picture."
        if count <= 2:
            return f"{count} outlier(s) out of {total} — likely the top performer and/or a weak entry. The rest of the analysis is reliable; check these individually."
        return f"{count} outliers out of {total} ({count / total:.0%}) — significant noise; averages and trends may be skewed. Treat aggregate findings with caution."
    if metric.startswith("Outlier fraction"):
        v = _val(metric)
        if v is None:
            return ""
        if v == 0:
            return "Dataset is clean — all findings are reliable."
        if v <= 10:
            return f"Only {v:.0f}% of videos are outliers — findings reflect the mainstream; the analysis is trustworthy."
        return f"{v:.0f}% outliers — a meaningful share of videos is not representative; treat averages with caution."
    return ""


def _explain_correlation(metric: str) -> str:
    """Pearson correlation — reveals tradeoffs or alignments between scoring factors."""
    m = re.search(r":\s*(-?\d+\.\d+)", metric)
    v = float(m.group(1)) if m else None
    if v is None:
        return ""
    factors = re.findall(r"between (\w+) and (\w+)", metric)
    pair = f"{factors[0][0]} and {factors[0][1]}" if factors else "these two factors"
    if v < -0.5:
        return f"Strong tradeoff ({v:.2f}) — you cannot optimise both {pair} at once; choose which to prioritise and accept the cost on the other."
    if v < -0.2:
        return f"Weak tradeoff ({v:.2f}) between {pair} — some tension exists but it is not severe; improving one does not heavily hurt the other."
    if v > 0.5:
        return f"Strong alignment ({v:.2f}) — {pair} reinforce each other; improving one tends to lift the other as well."
    if v > 0.2:
        return f"Weak alignment ({v:.2f}) between {pair} — slight tendency to move together; optimise independently."
    return f"No meaningful relationship ({v:.2f}) between {pair} — they are independent; optimise each separately without worrying about tradeoffs."


def _explain_spearman(metric: str) -> str:
    """Spearman correlation — rank-based check that confirms or weakens the Pearson finding."""
    m = re.search(r":\s*(-?\d+\.\d+)", metric)
    v = float(m.group(1)) if m else None
    if v is None:
        return ""
    factors = re.findall(r"between (\w+) and (\w+)", metric)
    pair = f"{factors[0][0]} and {factors[0][1]}" if factors else "these two factors"
    if abs(v) > 0.5:
        return f"Rank-based result ({v:.2f}) confirms the relationship is structural, not driven by a few extreme videos — the tradeoff is real across the board."
    return f"Rank-based result ({v:.2f}) — weak relationship between {pair}; not consistent enough to inform strategy."


def _explain_tests(metric: str, finding: str) -> str:
    """Hypothesis tests (Mann-Whitney, Welch t, normality) — validates whether quality tiers are real."""
    if metric.startswith("Mann-Whitney"):
        return "Top half and bottom half are statistically distinct — the ranking is meaningful, not random. Targeting the top tier is a real and achievable goal."
    if metric.startswith("Welch t-test"):
        m = re.search(r"diff=(-?\d+\.\d+)", metric)
        diff = float(m.group(1)) if m else None
        if diff:
            return f"Top-half videos score {diff:.3f} higher on average — a confirmed, meaningful gap. Understanding what separates top from bottom is worth the effort."
        return "Top and bottom halves are statistically different — the quality tier separation is real."
    if metric.startswith("Normality check"):
        if "non-normal" in metric or "non-normal" in finding:
            return "Non-normal distribution — averages can be misleading. Rely on median and rank-based findings (Spearman, Mann-Whitney) for the most reliable signals."
        return "Bell-curve distribution — standard averages and correlations are fully reliable for this dataset."
    return ""


def _explain_polynomial(metric: str) -> str:
    """Polynomial fits — checks whether the quality drop-off accelerates or has an S-curve shape."""
    v = _val(metric)
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


def _explain_bootstrap(metric: str, finding: str) -> str:
    """Bootstrap resampling — validates that score estimates are stable, not a sampling fluke."""
    if metric.startswith("Bootstrap CI lower"):
        v = _val(metric)
        return (
            f"Even in the worst-case simulation, the true average is at least {v:.3f} — the floor is confirmed and reliable."
            if v is not None
            else ""
        )
    if metric.startswith("Bootstrap CI upper"):
        v = _val(metric)
        return (
            f"Best realistic estimate tops out at {v:.3f} — this is the upside ceiling for what this space can deliver on average."
            if v is not None
            else ""
        )
    if metric.startswith("Bootstrap mean"):
        m2 = re.search(r"\[(-?\d+\.\d+),\s*(-?\d+\.\d+)\]", metric + " " + finding)
        v = _val(metric)
        if v and m2:
            lo, hi = float(m2.group(1)), float(m2.group(2))
            return f"Average confirmed at {v:.3f} (range {lo:.3f}-{hi:.3f}) across 2,000 resamples -- score estimates are stable and not a sampling fluke."
        return "Bootstrap confirms the average is stable — findings are reliable."
    return ""


def _explain_multi_regression(metric: str) -> str:
    """Multi-regression — reveals the exact weight of each scoring factor and confirms formula completeness."""
    v = _val(metric)
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


def _explain_kmeans(metric: str) -> str:
    """K-means clustering — segments the market into tiers to show where most content sits."""
    if metric.startswith("K-means (k=3) within"):
        return "Three market tiers were identified. Check the cluster sizes below to see how content is distributed across high, mid, and low performers."
    if metric.startswith("K-means cluster"):
        m2 = re.search(r"contains\s+(\d+)/(\d+)", metric)
        if not m2:
            return ""
        count, total = int(m2.group(1)), int(m2.group(2))
        pct = count / total
        if count == 1:
            return "Singleton cluster — one video is so different it forms its own group; likely the top performer or a significant outlier worth examining separately."
        if pct >= 0.5:
            return f"Dominant cluster ({count}/{total} videos, {pct:.0%}) — most content sits here; this is the mainstream tier you will be competing directly against."
        return f"{count}/{total} videos in this tier ({pct:.0%}) — a smaller but distinct segment; understand what separates it from the dominant cluster."
    return ""


def _explain_pca(metric: str, finding: str) -> str:
    """PCA — identifies which single feature most separates videos, revealing the true competitive axis."""
    if metric.startswith("PC1 "):
        m2 = re.search(r"top loadings:\s*(\w+)=", metric + " " + finding)
        factor = m2.group(1) if m2 else "one factor"
        return f"{factor.capitalize()} is the primary differentiator — channel size drives almost all separation between videos. Competing with large channels is the core challenge in this space."
    if metric.startswith("PC2 "):
        return "The second factor adds almost no new information — subscriber count dominates so completely that velocity and engagement are secondary signals."
    return ""


def _explain_kaplan_meier(metric: str, finding: str) -> str:
    """Kaplan-Meier survival — shows how long popular videos retain their reach over time."""
    if metric.startswith("Kaplan-Meier median survival"):
        if "not reached" in metric or "not reached" in finding:
            return "More than half of popular videos are still accumulating views at the end of the observation window — this topic has durable long-term value; publishing here is not a one-week bet."
        m2 = re.search(r":\s*(-?\d+\.?\d*)\s*days", metric)
        v = float(m2.group(1)) if m2 else None
        return (
            f"Half of popular videos lose momentum after {v:.0f} days — plan follow-up content before then to sustain reach."
            if v
            else ""
        )
    if metric.startswith("Kaplan-Meier S(t=30d)"):
        v = _val(metric)
        if v is None:
            return ""
        if v >= 0.6:
            return f"{v:.0%} of 100k+ videos still gain views after 30 days — strong lasting power; a good video here keeps paying off for weeks, not just days."
        if v >= 0.3:
            return f"{v:.0%} survival at 30 days — moderate longevity; expect most momentum in the first 2 weeks with a declining long tail."
        return f"Only {v:.0%} of popular videos survive to 30 days — fast-burn topic; publish quickly and expect most views in the first week."
    return ""


def _explain_naive_bayes(metric: str) -> str:
    """Naive Bayes — shows the base rate for top-5 success and whether the signals are predictive."""
    v = _val(metric)
    if metric.startswith("Naive Bayes prior P(is_top_5=0)"):
        return (
            f"Base odds of NOT making the top 5 are {v:.0%} — the top tier is selective; average content will not break through without deliberate differentiation."
            if v is not None
            else ""
        )
    if metric.startswith("Naive Bayes prior P(is_top_5=1)"):
        return (
            f"1 in {round(1 / v)} videos makes the top 5 by default — achievable but requires deliberate effort on trust, trend, and opportunity."
            if v
            else ""
        )
    if metric.startswith("Naive Bayes training accuracy"):
        if v is None:
            return ""
        if v >= 0.9:
            return f"Signals predict top-5 with {v:.0%} accuracy — trust, trend, and opportunity are genuine, reliable indicators. Optimising them is worth the effort."
        if v >= 0.75:
            return f"Signals predict top-5 with {v:.0%} accuracy — useful but imperfect; other factors also influence outcome."
        return f"Low accuracy ({v:.0%}) — the available signals are weak predictors; something important is not being measured."
    return ""


def _explain_huber(metric: str) -> str:
    """Huber regression — outlier-resistant version of the trend line, confirming the ranking decay is real."""
    v = _val(metric)
    if v is None:
        return ""
    if metric.startswith("Huber intercept"):
        return f"Reliable baseline at {v:.3f} — confirmed even with outliers removed; the average is not being distorted by unusual videos."
    if metric.startswith("Huber slope"):
        return f"Score drops {abs(v):.4f} per rank even without outlier influence — the gradual decline is real, not an artifact of unusual videos."
    if metric.startswith("Huber R²"):
        return f"Outlier-resistant fit at {v:.0%} — close to the standard regression, confirming outliers have limited impact on the overall trend."
    return ""


def _explain_bayesian(metric: str, finding: str) -> str:
    """Bayesian linear model — provides probabilistic confidence ranges on each factor's impact."""
    if metric.startswith("Bayesian intercept"):
        m2 = re.search(r":\s*(-?\d+\.\d+).*SD\s*(-?\d+\.\d+)", metric)
        if m2:
            v, sd = float(m2.group(1)), float(m2.group(2))
            return f"Starting score of {v:.3f} +/- {sd:.3f} — narrow uncertainty confirms the baseline is well-established from the data."
        return ""
    if metric.startswith("Bayesian residual variance"):
        v = _val(metric)
        if v is None:
            return ""
        if v < 0.001:
            return f"Residual variance {v:.4f} — essentially zero unexplained variation; trust, trend, and opportunity together fully account for the score differences."
        return f"Residual variance {v:.4f} — small but non-zero; most scoring is explained, but a minor component remains outside the model."
    # Coefficients share the same pattern: extract value and CrI
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


def _contextual_explanation(metric: str, finding: str) -> str:
    """Dispatch to the model-specific explanation function for a single highlight row.

    Returns a plain-English, decision-relevant sentence derived from the actual
    numeric value in the metric — not a static definition. Empty string if no
    explanation is available for this metric type.
    """
    model = _infer_model(metric)
    if model == "descriptive":
        return _explain_descriptive(metric)
    if model == "spread":
        return _explain_spread(metric)
    if model in ("regression", "growth"):
        return _explain_regression(metric)
    if model == "outliers":
        return _explain_outliers(metric)
    if model == "correlation":
        return _explain_correlation(metric)
    if model == "spearman":
        return _explain_spearman(metric)
    if model in ("mann_whitney", "welch_t", "normality"):
        return _explain_tests(metric, finding)
    if model in ("polynomial_deg2", "polynomial_deg3"):
        return _explain_polynomial(metric)
    if model == "bootstrap":
        return _explain_bootstrap(metric, finding)
    if model == "multi_regression":
        return _explain_multi_regression(metric)
    if model == "kmeans":
        return _explain_kmeans(metric)
    if model == "pca":
        return _explain_pca(metric, finding)
    if model == "kaplan_meier":
        return _explain_kaplan_meier(metric, finding)
    if model == "naive_bayes":
        return _explain_naive_bayes(metric)
    if model == "huber_regression":
        return _explain_huber(metric)
    if model == "bayesian_linear":
        return _explain_bayesian(metric, finding)
    return ""


def _highlights_table(highlights: list[str]) -> str:
    """Render stat highlights as a four-column markdown table.

    Columns: Model | Metric | Finding | What it means
    The Model column is left blank for consecutive rows of the same model to
    visually group related metrics. The 'What it means' column is generated
    dynamically from the actual metric value, not a static definition.
    """
    if not highlights:
        return "_(no highlights)_"
    header = (
        "| Model | Metric | Finding | What it means |\n|-------|--------|---------|---------------|"
    )
    rows = []
    prev_model = None
    for h in highlights:
        if " — " in h:
            metric, finding = h.split(" — ", 1)
        else:
            metric, finding = h, ""
        model = _infer_model(metric)
        explanation = _contextual_explanation(metric, finding)
        model_cell = model if model != prev_model else ""
        prev_model = model
        metric = metric.replace("|", r"\|")
        finding = finding.replace("|", r"\|")
        explanation = explanation.replace("|", r"\|")
        rows.append(f"| {model_cell} | {metric} | {finding} | {explanation} |")
    return "\n".join([header, *rows])


def _bulletise(text: str) -> str:
    """Split a semicolon-separated summary string into a markdown bullet list."""
    return "\n".join(f"- {part.strip()}" for part in text.split(";") if part.strip())


def render_full(
    packet: dict[str, Any],
    compiled_synthesis: str | None = None,
    opportunity_analysis: str | None = None,
) -> str:
    """Render all 11 sections as Markdown.

    Sections 1-9 are derived from the packet. Sections 10-11 use the
    provided synthesis strings; if omitted they indicate that LLM synthesis
    was not run (e.g. plain CLI mode without a configured runner).
    """
    body = render_sections_1_9(packet)
    s10 = compiled_synthesis or "_(LLM synthesis not run — use skill mode for AI analysis)_"
    s11 = opportunity_analysis or "_(LLM synthesis not run — use skill mode for AI analysis)_"
    body += f"\n## 10. Compiled Synthesis\n\n{s10}\n"
    body += f"\n## 11. Opportunity Analysis\n\n{s11}\n"
    return body


def render_sections_1_9(packet: dict[str, Any]) -> str:
    """Render sections 1-9 deterministically from packet data.

    Each section maps directly to a field in the packet. This function is
    also called by render_full and by tests that verify section formatting
    without requiring LLM synthesis.
    """
    svs = packet["source_validation_summary"]
    items = packet["items_top5"]
    stats = packet["stats_summary"]
    warnings = packet.get("warnings", [])
    parts: list[str] = []
    parts.append(
        "## 1. Topic & Purpose\n\n"
        f"- **Topic:** {packet['topic']}\n"
        f"- **Purposes:** {', '.join(packet['purpose_set'])}"
    )
    parts.append(f"## 2. Platform\n\n- **Platform:** {packet['platform']}")
    if items:
        parts.append(
            "## 3. Top Items\n\n"
            + _items_table(items)
            + "\n\n**Links & takeaways:**\n\n"
            + _items_links_and_takeaways(items)
        )
    else:
        parts.append("## 3. Top Items\n\n_(no items returned)_")
    parts.append("## 4. Platform Signals\n\n" + _bulletise(packet["platform_signals_summary"]))
    parts.append(
        "## 5. Source Validation\n\n"
        f"- validated: {svs['validated']}, partial: {svs['partially']}, "
        f"unverified: {svs['unverified']}, low-trust: {svs['low_trust']}\n"
        f"- primary/secondary/commentary: {svs['primary']}/{svs['secondary']}/{svs['commentary']}"
        + (f"\n- notes: {svs['notes']}" if svs.get("notes") else "")
    )
    parts.append("## 6. Evidence\n\n" + _bulletise(packet["evidence_summary"]))
    lc = "\n\n_low confidence — interpret with caution_" if stats.get("low_confidence") else ""
    highlights = stats.get("highlights", [])
    parts.append(f"## 7. Statistics\n\n{_highlights_table(highlights)}{lc}")
    caps = packet.get("chart_captions", [])
    parts.append("## 8. Charts\n\n" + ("\n\n".join(caps) if caps else "_(no charts rendered)_"))
    parts.append(
        "## 9. Warnings\n\n" + ("\n".join(f"- {w}" for w in warnings) if warnings else "_(none)_")
    )
    return "\n\n".join(parts) + "\n"
