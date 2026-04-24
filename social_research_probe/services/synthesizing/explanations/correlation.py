"""Explanations for correlation, outlier, and hypothesis-test statistics."""

from __future__ import annotations

import re

from ._common import parse_numeric


def explain_correlation(metric: str) -> str:
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


def explain_spearman(metric: str) -> str:
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


def explain_outliers(metric: str) -> str:
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
        v = parse_numeric(metric)
        if v is None:
            return ""
        if v == 0:
            return "Dataset is clean — all findings are reliable."
        if v <= 10:
            return f"Only {v:.0f}% of videos are outliers — findings reflect the mainstream; the analysis is trustworthy."
        return f"{v:.0f}% outliers — a meaningful share of videos is not representative; treat averages with caution."
    return ""


def explain_tests(metric: str, finding: str) -> str:
    """Hypothesis tests (Mann-Whitney, Welch t, normality) — validates quality-tier separation."""
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
