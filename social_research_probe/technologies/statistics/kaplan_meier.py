"""Kaplan-Meier non-parametric survival estimator — pure Python.

Given per-item event indicator (1 = event observed, 0 = censored) and
observation time, returns the estimated survival function S(t) and a
few summary StatResults (median survival, survival at a given horizon).
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult


def run(
    times: list[float],
    events: list[int],
    label: str = "event",
    horizon_days: float = 30.0,
) -> list[StatResult]:
    """Fit Kaplan-Meier and return median survival + S(t=horizon)."""
    n = len(times)
    if n == 0 or n != len(events):
        return []
    if sum(events) == 0:
        return [
            StatResult(
                name=f"km_no_events_{label}",
                value=0.0,
                caption=f"Kaplan-Meier for {label}: no events observed in {n} items",
            )
        ]
    curve = fit(times, events)
    median = _median_survival(curve)
    at_horizon = survival_at(curve, horizon_days)
    results = [
        StatResult(
            name=f"km_median_{label}",
            value=median if median is not None else float("inf"),
            caption=(
                f"Kaplan-Meier median survival for {label}: "
                f"{'not reached (>50% survive)' if median is None else f'{median:.1f} days'}"
            ),
        ),
        StatResult(
            name=f"km_s_at_{int(horizon_days)}d_{label}",
            value=at_horizon,
            caption=(f"Kaplan-Meier S(t={horizon_days:.0f}d) for {label}: {at_horizon:.3f}"),
        ),
    ]
    return results


def fit(times: list[float], events: list[int]) -> list[tuple[float, float]]:
    """Return the survival curve as a list of (time, survival) points."""
    if len(times) != len(events):
        return []
    rows = sorted(zip(times, events, strict=True), key=lambda r: r[0])
    survival = 1.0
    at_risk = len(rows)
    curve: list[tuple[float, float]] = [(0.0, 1.0)]
    i = 0
    while i < len(rows):
        t = rows[i][0]
        d = 0
        while i < len(rows) and rows[i][0] == t:
            d += rows[i][1]
            i += 1
        if d > 0 and at_risk > 0:
            survival *= 1 - d / at_risk
        at_risk -= i - (i - d)
        at_risk = _recount_at_risk(rows, t)
        curve.append((t, survival))
    return curve


def _recount_at_risk(rows: list[tuple[float, int]], t: float) -> int:
    return sum(1 for rt, _ in rows if rt > t)


def _median_survival(curve: list[tuple[float, float]]) -> float | None:
    for t, s in curve:
        if s <= 0.5:
            return t
    return None


def survival_at(curve: list[tuple[float, float]], t: float) -> float:
    last = 1.0
    for point_t, point_s in curve:
        if point_t > t:
            return last
        last = point_s
    return last
