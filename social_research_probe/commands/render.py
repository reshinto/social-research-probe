"""commands/render.py — CLI command to render charts and stats for a research report.

Takes a research report (produced by run-research) and generates:
  - Statistical summaries of the top-N items' scores.
  - Chart images saved as PNG files.
  - A text report with section captions.

This lets users inspect research results offline, outside of the AI skill flow.

Called by: cli._dispatch when args.command == 'render'.
"""

from __future__ import annotations

import json
import sys

from social_research_probe.technologies.charts.selector import select_and_render
from social_research_probe.technologies.statistics.selector import select_and_run
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.core.report import unwrap_report


def _load_report(report_path: str) -> dict:
    """Load and validate report JSON file."""
    from social_research_probe.utils.core.errors import ValidationError

    try:
        with open(report_path) as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValidationError(f"cannot read report file: {exc}") from exc
    report = unwrap_report(payload)
    if not isinstance(report, dict):
        raise ValidationError("report file must contain a JSON object")
    return report


def _extract_overall_scores(report: dict) -> list[float]:
    """Extract overall scores from items in report."""
    items = report.get("items_top_n", [])
    return [it.get("scores", {}).get("overall", 0.0) for it in items]


def _format_report(stat_results, chart) -> dict:
    """Format stats and chart into report structure."""
    return {
        "stats": [{"name": r.name, "value": r.value, "caption": r.caption} for r in stat_results],
        "chart": {"path": chart.path, "caption": chart.caption},
    }


def run(report_path: str, output_dir: str | None = None) -> int:
    """Read a report JSON file and render stats + charts for the top-N items.

    Loads the report, extracts the "overall" score from each top-N item,
    passes those scores to the stats and viz selectors, then prints a JSON
    report with stat names/values/captions and chart path/caption to stdout.

    Args:
        report_path: Path to the JSON report file produced by run-research.
        output_dir: Directory to save chart image files. If None, the viz
            selector uses a system temp directory.

    Returns:
        Exit code (0 on success).

    Raises:
        ValidationError: If report_path does not exist, cannot be opened, or
            is not valid JSON.
    """
    report = _load_report(report_path)
    overall_scores = _extract_overall_scores(report)
    stat_results = select_and_run(overall_scores, label="overall_score")
    chart = select_and_render(overall_scores, label="overall_score", output_dir=output_dir)
    report = _format_report(stat_results, chart)
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    return ExitCode.SUCCESS
