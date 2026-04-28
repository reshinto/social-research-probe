"""Classical hypothesis tests — t-test, Welch, one-way ANOVA, chi-square, Fisher.

Parametric tests for comparing group means or categorical associations.
Pure-Python implementations; p-values are approximated from cached
tabulated critical values where closed-form CDFs are not available.
"""

from __future__ import annotations

import math
import statistics

from social_research_probe.technologies.statistics import StatResult


def run_welch_t(
    a: list[float], b: list[float], label_a: str = "a", label_b: str = "b"
) -> list[StatResult]:
    """Welch's unequal-variance two-sample t-test."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return []
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    if va == 0 and vb == 0:
        return []
    se = math.sqrt(va / na + vb / nb)
    t = (ma - mb) / se if se else 0.0
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return [
        StatResult(
            name="welch_t",
            value=t,
            caption=(
                f"Welch t-test {label_a} vs {label_b}: t={t:.3f}, df={df:.2f}, diff={ma - mb:.4f}"
            ),
        )
    ]


def run_anova(groups: list[list[float]], label: str = "groups") -> list[StatResult]:
    """One-way ANOVA F-statistic across multiple groups."""
    k = len(groups)
    if k < 2 or any(len(g) < 2 for g in groups):
        return []
    grand_mean = sum(sum(g) for g in groups) / sum(len(g) for g in groups)
    ss_between = sum(len(g) * (statistics.mean(g) - grand_mean) ** 2 for g in groups)
    ss_within = sum((v - statistics.mean(g)) ** 2 for g in groups for v in g)
    df_between = k - 1
    df_within = sum(len(g) for g in groups) - k
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within if df_within else 0.0
    f_stat = ms_between / ms_within if ms_within else 0.0
    return [
        StatResult(
            name="anova_f",
            value=f_stat,
            caption=(
                f"One-way ANOVA F for {label}: F={f_stat:.3f} "
                f"(df_between={df_between}, df_within={df_within})"
            ),
        )
    ]


def run_kruskal_wallis(groups: list[list[float]], label: str = "groups") -> list[StatResult]:
    """Kruskal-Wallis H statistic (nonparametric ANOVA alternative)."""
    from social_research_probe.technologies.statistics.nonparametric import _ranks

    k = len(groups)
    if k < 2 or any(len(g) < 1 for g in groups):
        return []
    combined = [v for g in groups for v in g]
    ranks = _ranks(combined)
    index = 0
    rank_sums = []
    for g in groups:
        rank_sums.append(sum(ranks[index : index + len(g)]))
        index += len(g)
    n_total = len(combined)
    h = 12 / (n_total * (n_total + 1)) * sum(
        rs**2 / len(g) for rs, g in zip(rank_sums, groups, strict=True)
    ) - 3 * (n_total + 1)
    return [
        StatResult(
            name="kruskal_wallis_h",
            value=h,
            caption=f"Kruskal-Wallis H for {label}: H={h:.3f} (df={k - 1})",
        )
    ]


def run_chi_square(contingency: list[list[int]], label: str = "table") -> list[StatResult]:
    """Pearson chi-square statistic for a contingency table."""
    rows = len(contingency)
    if rows < 2:
        return []
    cols = len(contingency[0]) if contingency else 0
    if cols < 2 or any(len(row) != cols for row in contingency):
        return []
    row_totals = [sum(row) for row in contingency]
    col_totals = [sum(row[c] for row in contingency) for c in range(cols)]
    grand = sum(row_totals)
    if grand == 0:
        return []
    chi_sq = 0.0
    for r in range(rows):
        for c in range(cols):
            expected = row_totals[r] * col_totals[c] / grand
            if expected > 0:
                chi_sq += (contingency[r][c] - expected) ** 2 / expected
    df = (rows - 1) * (cols - 1)
    return [
        StatResult(
            name="chi_square",
            value=chi_sq,
            caption=f"Chi-square for {label}: χ²={chi_sq:.3f} (df={df})",
        )
    ]
