"""Statistical analysis technology adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology

_NUMERIC_TARGETS: tuple[str, ...] = (
    "overall",
    "trust",
    "trend",
    "opportunity",
    "view_velocity",
    "engagement_ratio",
    "age_days",
    "subscribers",
    "views",
)


@dataclass
class StatResult:
    """The output of a single statistical analysis.

    Keeping these fields together makes pipeline handoffs easier to inspect and harder to
    accidentally reorder.

    Examples:
        Input:
            StatResult
        Output:
            StatResult
    """

    name: str
    value: float
    caption: str


def items_from_data(data: object) -> list[dict]:
    """Extract scored_items list from input data dict.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            items_from_data(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    if not isinstance(data, dict):
        return []
    return [d for d in data.get("scored_items", []) if isinstance(d, dict)]


def _build_targets_dict(items: list[dict]) -> dict[str, list]:
    """Build the targets dict structure consumed by the next step.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _build_targets_dict(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    from social_research_probe.utils.analyzing.targets import build_targets

    return build_targets(items)


def _numeric_series(targets: dict[str, list], label: str) -> list[float]:
    """Document the numeric series rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        targets: Feature matrix, feature names, or target columns used by analysis helpers.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _numeric_series(
                targets=["views", "likes"],
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    return [float(v) for v in targets.get(label, [])]


def _run_for_label(series: list[float], label: str) -> list:
    """Document the run for label rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        series: Numeric series used by the statistical calculation.
        label: Human-readable metric label included in statistical and chart outputs.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _run_for_label(
                series=[1.0, 2.0, 3.0],
                label="engagement",
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    from social_research_probe.technologies.statistics.selector import select_and_run

    return select_and_run(series, label=label)


def _stats_per_target(targets: dict[str, list]) -> dict[str, list]:
    """Document the stats per target rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        targets: Feature matrix, feature names, or target columns used by analysis helpers.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _stats_per_target(
                targets=["views", "likes"],
            )
        Output:
            {"enabled": True}
    """
    results: dict[str, list] = {}
    for label in _NUMERIC_TARGETS:
        series = _numeric_series(targets, label)
        if not series:
            continue
        results[label] = _run_for_label(series, label)
    return results


def _highlight_lines(by_target: dict[str, list]) -> list[str]:
    """Build the highlight lines used in generated methodology output.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        by_target: Feature matrix, feature names, or target columns used by analysis helpers.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _highlight_lines(
                by_target=["views", "likes"],
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    return [
        getattr(r, "caption", "")
        for results in by_target.values()
        for r in results
        if getattr(r, "caption", "")
    ]


def _is_low_confidence(items: list[dict]) -> bool:
    """Return whether is low confidence is true for the input.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_low_confidence(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            True
    """
    return len(items) < 5


def _compute(items: list[dict]) -> dict:
    """Document the compute rule at the boundary where callers use it.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _compute(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    if not items:
        return {"highlights": [], "low_confidence": True}
    by_target = _stats_per_target(_build_targets_dict(items))
    return {
        "highlights": _highlight_lines(by_target),
        "low_confidence": _is_low_confidence(items),
    }


async def compute_async(items: list[dict]) -> dict:
    """Run stats computation in a thread to avoid blocking the event loop.

    Statistics helpers return compact report records, keeping mathematical details close to the
    label and interpretation shown in reports.

    Args:
        items: Ordered source items being carried through the current pipeline step.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            await compute_async(
                items=[{"title": "Example", "url": "https://youtu.be/demo"}],
            )
        Output:
            {"enabled": True}
    """
    return await asyncio.to_thread(_compute, items)


class StatisticsTech(BaseTechnology[object, dict]):
    """Technology wrapper for computing statistics across all targets.

    Examples:
        Input:
            StatisticsTech
        Output:
            StatisticsTech
    """

    name: ClassVar[str] = "stats_per_target"
    enabled_config_key: ClassVar[str] = "stats_per_target"

    async def _execute(self, input_data: object) -> dict:
        """Run this component and return the project-shaped output expected by its service.

        Statistics helpers return compact report records, keeping mathematical details close to the
        label and interpretation shown in reports.

        Args:
            input_data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    input_data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                {"enabled": True}
        """
        return await compute_async(items_from_data(input_data))
