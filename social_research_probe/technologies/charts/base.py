"""Shared result type for all chart-rendering modules.

Every viz module returns a ChartResult so callers can handle file paths and
captions uniformly regardless of which chart type was produced.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChartResult:
    """The output of a chart-rendering function.

    Attributes:
        path: Absolute path to the saved PNG file.
        caption: Human-readable description of the chart, e.g.
                 'Line chart: view velocity over time'.
    """

    path: str
    caption: str
