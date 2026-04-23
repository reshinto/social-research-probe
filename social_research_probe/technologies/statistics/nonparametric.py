"""Nonparametric tests — Spearman rank correlation and Mann-Whitney U.

When residuals are non-normal, outliers dominate, or the sample is small,
nonparametric tests give more trustworthy inference than their parametric
siblings. This module ships pure-Python implementations so the rest of
the pipeline has a robust alternative to Pearson and the independent
t-test.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics.base import StatResult


def run_spearman(
    a: list[float], b: list[float], label_a: str = "a", label_b: str = "b"
) -> list[StatResult]:
    """Return Spearman's rank correlation coefficient for two equal-length series."""
    n = len(a)
    if n < 2 or n != len(b):
        return []
    ranks_a = _ranks(a)
    ranks_b = _ranks(b)
    mean_a = sum(ranks_a) / n
    mean_b = sum(ranks_b) / n
    num = sum((ra - mean_a) * (rb - mean_b) for ra, rb in zip(ranks_a, ranks_b, strict=True))
    den_a = sum((ra - mean_a) ** 2 for ra in ranks_a)
    den_b = sum((rb - mean_b) ** 2 for rb in ranks_b)
    denom = (den_a * den_b) ** 0.5
    rho = num / denom if denom else 0.0
    return [
        StatResult(
            name="spearman_rho",
            value=rho,
            caption=f"Spearman's rho between {label_a} and {label_b}: {rho:.4f}",
        )
    ]


def run_mann_whitney(
    group_a: list[float], group_b: list[float], label_a: str = "a", label_b: str = "b"
) -> list[StatResult]:
    """Return the Mann-Whitney U statistic and a tie-aware z approximation."""
    na = len(group_a)
    nb = len(group_b)
    if na < 1 or nb < 1:
        return []
    combined = [(v, "a") for v in group_a] + [(v, "b") for v in group_b]
    ranks = _ranks_for_pairs(combined)
    rank_sum_a = sum(r for (_, group), r in zip(combined, ranks, strict=True) if group == "a")
    u_a = rank_sum_a - na * (na + 1) / 2
    u_b = na * nb - u_a
    u = min(u_a, u_b)
    mean_u = na * nb / 2
    std_u = (na * nb * (na + nb + 1) / 12) ** 0.5
    z = (u - mean_u) / std_u if std_u else 0.0
    return [
        StatResult(
            name="mann_whitney_u",
            value=u,
            caption=f"Mann-Whitney U between {label_a} and {label_b}: U={u:.2f} (z={z:.3f})",
        )
    ]


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        mean_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = mean_rank
        i = j + 1
    return ranks


def _ranks_for_pairs(pairs: list[tuple[float, str]]) -> list[float]:
    return _ranks([v for v, _ in pairs])
