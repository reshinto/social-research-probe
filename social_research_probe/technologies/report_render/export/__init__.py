"""Export artifact technologies: CSV, markdown, and JSON builders."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.pipeline.helpers import resolve_html_report_path


def _write_sources(report: dict, reports_dir: Path, stem: str) -> str:
    from social_research_probe.technologies.report_render.export.sources_csv import (
        build_sources_rows,
        write_sources_csv,
    )

    rows = build_sources_rows(report.get("items_top_n") or [])
    path = reports_dir / f"{stem}-sources.csv"
    return str(write_sources_csv(rows, path))


def _write_comments(report: dict, reports_dir: Path, stem: str) -> str:
    from social_research_probe.technologies.report_render.export.comments_csv import (
        build_comments_rows,
        write_comments_csv,
    )

    rows = build_comments_rows(report.get("items_top_n") or [])
    path = reports_dir / f"{stem}-comments.csv"
    return str(write_comments_csv(rows, path))


def _write_methodology(report: dict, config: dict, reports_dir: Path, stem: str) -> str:
    from social_research_probe.technologies.report_render.export.methodology_md import (
        build_methodology,
        write_methodology,
    )

    content = build_methodology(report, config)
    path = reports_dir / f"{stem}-methodology.md"
    return str(write_methodology(content, path))


def _write_run_summary(
    report: dict,
    config: dict,
    artifact_paths: dict[str, str],
    reports_dir: Path,
    stem: str,
) -> str:
    from social_research_probe.technologies.report_render.export.run_summary_json import (
        build_run_summary,
        write_run_summary,
    )

    summary = build_run_summary(report, config, artifact_paths)
    path = reports_dir / f"{stem}-run_summary.json"
    return str(write_run_summary(summary, path))


class ExportPackageTech(BaseTechnology[dict, dict[str, str]]):
    """Write export artifacts (CSV, markdown, JSON) alongside the HTML report."""

    name: ClassVar[str] = "export_package"
    enabled_config_key: ClassVar[str] = "export_package"

    async def _execute(self, data: dict) -> dict[str, str]:
        report = data.get("report") or {}
        config = data.get("config") or {}
        stem = data.get("stem") or "export"
        reports_dir = Path(data.get("reports_dir") or ".")
        reports_dir.mkdir(parents=True, exist_ok=True)

        export_cfg = config.get("export") or {}
        if not export_cfg.get("enabled", True):
            return {}

        paths: dict[str, str] = {}
        if export_cfg.get("sources_csv", True):
            paths["sources_csv"] = _write_sources(report, reports_dir, stem)
        if export_cfg.get("comments_csv", True):
            paths["comments_csv"] = _write_comments(report, reports_dir, stem)
        if export_cfg.get("methodology_md", True):
            paths["methodology_md"] = _write_methodology(report, config, reports_dir, stem)
        if export_cfg.get("run_summary_json", True):
            summary_paths = dict(paths)
            html_path = resolve_html_report_path(report)
            if html_path is not None:
                summary_paths["html_report"] = str(html_path)
            paths["run_summary_json"] = _write_run_summary(
                report, config, summary_paths, reports_dir, stem
            )
        return paths
