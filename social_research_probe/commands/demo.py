"""commands/demo.py — Generate an offline synthetic demo report and exports.

Builds a fully populated synthetic ResearchReport, renders it through the
existing ReportService for HTML, and writes the four export artifacts via
ExportService. No API keys, no LLM, no network — only local file I/O.

Output goes to ``<data_dir>/reports/`` alongside real research artifacts.
The ``[SYNTHETIC DEMO]`` topic prefix yields a slug that visibly identifies
demo files, and the disclaimer surfaces in every artifact through existing
renderer hooks (warnings, compiled_synthesis, report_summary).

Usage:
    srp demo-report
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from social_research_probe.commands._demo_fixtures import build_demo_report
from social_research_probe.config import load_active_config
from social_research_probe.services.reporting.export import ExportService
from social_research_probe.services.reporting.report import ReportService
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.display.progress import log_with_time
from social_research_probe.utils.pipeline.helpers import resolve_html_report_path


async def _render_html(report: dict) -> None:
    """Render the report via ReportService and stamp report_path on the dict."""
    result = (await ReportService().execute_batch([{"report": report, "allow_html": True}]))[0]
    report_path = next(
        (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, str)),
        "",
    )
    report["report_path"] = report_path


async def _run_exports(
    report: dict,
    platform_cfg: dict,
    stem: str,
    reports_dir: Path,
) -> dict[str, str]:
    """Write export artifacts via ExportService; return {kind: path} dict."""
    result = (
        await ExportService().execute_batch(
            [
                {
                    "report": report,
                    "config": platform_cfg,
                    "stem": stem,
                    "reports_dir": reports_dir,
                }
            ]
        )
    )[0]
    return next(
        (tr.output for tr in result.tech_results if tr.success and isinstance(tr.output, dict)),
        {},
    )


def _print_paths(report_path: str, export_paths: dict[str, str]) -> None:
    """Write report_path then each export path to stdout, one per line."""
    sys.stdout.write(f"{report_path}\n")
    for path in export_paths.values():
        sys.stdout.write(f"{path}\n")
    sys.stdout.flush()


@log_with_time("[srp] demo-report")
def run(args: argparse.Namespace) -> int:
    """Generate the offline synthetic demo report and export package."""
    del args
    cfg = load_active_config()
    report = build_demo_report()
    asyncio.run(_render_html(report))
    html_path = resolve_html_report_path(report)
    if html_path is None:
        return ExitCode.SUCCESS
    platform_cfg = cfg.platform_defaults("youtube")
    export_paths = asyncio.run(_run_exports(report, platform_cfg, html_path.stem, html_path.parent))
    report["export_paths"] = export_paths
    _print_paths(report["report_path"], export_paths)
    return ExitCode.SUCCESS
