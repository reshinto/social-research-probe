"""Explanations for k-means clustering, PCA, and Kaplan-Meier survival models."""

from __future__ import annotations

import re

from ._common import parse_numeric


def explain_kmeans(metric: str) -> str:
    """K-means clustering — segments the market into tiers."""
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


def explain_pca(metric: str, finding: str) -> str:
    """PCA — identifies which feature most separates videos, revealing the true competitive axis."""
    if metric.startswith("PC1 "):
        m2 = re.search(r"top loadings:\s*(\w+)=", metric + " " + finding)
        factor = m2.group(1) if m2 else "one factor"
        return f"{factor.capitalize()} is the primary differentiator — channel size drives almost all separation between videos. Competing with large channels is the core challenge in this space."
    if metric.startswith("PC2 "):
        return "The second factor adds almost no new information — subscriber count dominates so completely that velocity and engagement are secondary signals."
    return ""


def explain_kaplan_meier(metric: str, finding: str) -> str:
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
        v = parse_numeric(metric)
        if v is None:
            return ""
        if v >= 0.6:
            return f"{v:.0%} of 100k+ videos still gain views after 30 days — strong lasting power; a good video here keeps paying off for weeks, not just days."
        if v >= 0.3:
            return f"{v:.0%} survival at 30 days — moderate longevity; expect most momentum in the first 2 weeks with a declining long tail."
        return f"Only {v:.0%} of popular videos survive to 30 days — fast-burn topic; publish quickly and expect most views in the first week."
    return ""
