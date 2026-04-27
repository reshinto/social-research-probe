"""Shared result type for all statistical analysis modules.

Every stats module returns a list of StatResult objects so callers can
handle results uniformly without knowing which analysis was run.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StatResult:
    """The output of a single statistical analysis.

    Attributes:
        name: Short identifier, e.g. 'mean_views' or 'growth_rate'.
        value: Numeric result of the calculation.
        caption: Human-readable sentence explaining the result, e.g.
                 'Average views per item: 12,345'.
    """

    name: str
    value: float
    caption: str
