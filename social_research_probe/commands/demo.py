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

from social_research_probe.config import Config, load_active_config
from social_research_probe.services.persistence import PersistenceService
from social_research_probe.services.reporting.export import ExportService
from social_research_probe.services.reporting.report import ReportService
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.demo.fixtures import build_demo_report
from social_research_probe.utils.display.progress import log_with_time
from social_research_probe.utils.pipeline.helpers import resolve_html_report_path


async def _render_html(report: dict) -> None:
    """Render the report via ReportService and stamp report_path on the dict.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            await _render_html(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            None
    """
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
    """Write export artifacts via ExportService; return {kind: path} dict.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        platform_cfg: Configuration or context values that control this run.
        stem: Filename stem used to keep related export artifacts grouped together.
        reports_dir: Filesystem location used to read, write, or resolve project data.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            await _run_exports(
                report={"topic": "AI safety", "items_top_n": []},
                platform_cfg={"enabled": True},
                stem="report",
                reports_dir=Path(".skill-data"),
            )
        Output:
            {"enabled": True}
    """
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


async def _persist_if_enabled(report: dict, cfg: Config) -> None:
    """Persist demo report to SQLite when database persistence is enabled.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        cfg: Configuration or context values that control this run.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            await _persist_if_enabled(
                report={"topic": "AI safety", "items_top_n": []},
                cfg={"enabled": True},
            )
        Output:
            None
    """
    db_cfg: dict = cfg.raw.get("database") or {}
    if not db_cfg.get("enabled", True):
        return
    payload = {
        "report": report,
        "db_path": cfg.database_path,
        "config": cfg.raw,
        "persist_transcript_text": db_cfg.get("persist_transcript_text", False),
        "persist_comment_text": db_cfg.get("persist_comment_text", True),
    }
    results = await PersistenceService().execute_batch([payload])
    for r in results:
        for tr in r.tech_results:
            if not tr.success:
                report.setdefault("warnings", []).append(
                    f"persistence: {tr.error or 'sqlite persist failed'}"
                )


def _print_paths(report_path: str, export_paths: dict[str, str]) -> None:
    """Write report_path then each export path to stdout, one per line.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.
        export_paths: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _print_paths(
                report_path=Path("report.html"),
                export_paths=Path("report.html"),
            )
        Output:
            None
    """
    sys.stdout.write(f"{report_path}\n")
    for path in export_paths.values():
        sys.stdout.write(f"{path}\n")
    sys.stdout.flush()


@log_with_time("[srp] demo-report")
def run(args: argparse.Namespace) -> int:
    """Generate the offline synthetic demo report and export package.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

    Args:
        args: Parsed argparse namespace for the command being dispatched.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                args=argparse.Namespace(output="json"),
            )
        Output:
            5
    """
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
    asyncio.run(_persist_if_enabled(report, cfg))
    _print_paths(str(html_path), export_paths)
    return ExitCode.SUCCESS
