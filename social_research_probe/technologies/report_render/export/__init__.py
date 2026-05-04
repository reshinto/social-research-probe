"""Export artifact technologies: CSV, markdown, and JSON builders."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.pipeline.helpers import resolve_html_report_path


def _write_sources(report: dict, reports_dir: Path, stem: str) -> str:
    """Create sources output for users or downstream tools.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        reports_dir: Filesystem location used to read, write, or resolve project data.
        stem: Filename stem used to keep related export artifacts grouped together.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_sources(
                report={"topic": "AI safety", "items_top_n": []},
                reports_dir=Path(".skill-data"),
                stem="report",
            )
        Output:
            None
    """
    from social_research_probe.technologies.report_render.export.sources_csv import (
        build_sources_rows,
        write_sources_csv,
    )

    rows = build_sources_rows(report.get("items_top_n") or [])
    path = reports_dir / f"{stem}-sources.csv"
    return str(write_sources_csv(rows, path))


def _write_comments(report: dict, reports_dir: Path, stem: str) -> str:
    """Create comments output for users or downstream tools.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        reports_dir: Filesystem location used to read, write, or resolve project data.
        stem: Filename stem used to keep related export artifacts grouped together.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_comments(
                report={"topic": "AI safety", "items_top_n": []},
                reports_dir=Path(".skill-data"),
                stem="report",
            )
        Output:
            None
    """
    from social_research_probe.technologies.report_render.export.comments_csv import (
        build_comments_rows,
        write_comments_csv,
    )

    rows = build_comments_rows(report.get("items_top_n") or [])
    path = reports_dir / f"{stem}-comments.csv"
    return str(write_comments_csv(rows, path))


def _write_methodology(report: dict, config: dict, reports_dir: Path, stem: str) -> str:
    """Create methodology output for users or downstream tools.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        config: Configuration or context values that control this run.
        reports_dir: Filesystem location used to read, write, or resolve project data.
        stem: Filename stem used to keep related export artifacts grouped together.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_methodology(
                report={"topic": "AI safety", "items_top_n": []},
                config={"enabled": True},
                reports_dir=Path(".skill-data"),
                stem="report",
            )
        Output:
            None
    """
    from social_research_probe.technologies.report_render.export.methodology_md import (
        build_methodology,
        write_methodology,
    )

    content = build_methodology(report, config)
    path = reports_dir / f"{stem}-methodology.md"
    return str(write_methodology(content, path))


def _write_claims(report: dict, reports_dir: Path, stem: str) -> str:
    """Create claims output for users or downstream tools.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        reports_dir: Filesystem location used to read, write, or resolve project data.
        stem: Filename stem used to keep related export artifacts grouped together.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_claims(
                report={"topic": "AI safety", "items_top_n": []},
                reports_dir=Path(".skill-data"),
                stem="report",
            )
        Output:
            None
    """
    from social_research_probe.technologies.report_render.export.claims_csv import (
        build_claims_rows,
        write_claims_csv,
    )

    rows = build_claims_rows(report.get("items_top_n") or [])
    path = reports_dir / f"{stem}-claims.csv"
    return str(write_claims_csv(rows, path))


def _write_narratives(report: dict, reports_dir: Path, stem: str) -> str:
    """Write narrative clusters CSV export.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        reports_dir: Filesystem location used to read, write, or resolve project data.
        stem: Filename stem used to keep related export artifacts grouped together.

    Returns:
        String path of the written CSV file.

    Examples:
        Input:
            _write_narratives(
                report={"narratives": [{"narrative_id": "abc"}]},
                reports_dir=Path(".skill-data"),
                stem="report",
            )
        Output:
            ".skill-data/report-narratives.csv"
    """
    from social_research_probe.technologies.report_render.export.narratives_csv import (
        build_narratives_rows,
        write_narratives_csv,
    )

    rows = build_narratives_rows(report.get("narratives") or [])
    path = reports_dir / f"{stem}-narratives.csv"
    return str(write_narratives_csv(rows, path))


def _write_run_summary(
    report: dict,
    config: dict,
    artifact_paths: dict[str, str],
    reports_dir: Path,
    stem: str,
) -> str:
    """Create run summary output for users or downstream tools.

    The report pipeline needs a predictable text payload even when transcripts or summaries are
    missing.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        config: Configuration or context values that control this run.
        artifact_paths: Filesystem location used to read, write, or resolve project data.
        reports_dir: Filesystem location used to read, write, or resolve project data.
        stem: Filename stem used to keep related export artifacts grouped together.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_run_summary(
                report={"topic": "AI safety", "items_top_n": []},
                config={"enabled": True},
                artifact_paths=Path("report.html"),
                reports_dir=Path(".skill-data"),
                stem="report",
            )
        Output:
            None
    """
    from social_research_probe.technologies.report_render.export.run_summary_json import (
        build_run_summary,
        write_run_summary,
    )

    summary = build_run_summary(report, config, artifact_paths)
    path = reports_dir / f"{stem}-run_summary.json"
    return str(write_run_summary(summary, path))


class ExportPackageTech(BaseTechnology[dict, dict[str, str]]):
    """Write export artifacts (CSV, markdown, JSON) alongside the HTML report.

    Examples:
        Input:
            ExportPackageTech
        Output:
            ExportPackageTech
    """

    name: ClassVar[str] = "export_package"
    enabled_config_key: ClassVar[str] = "export_package"

    async def _execute(self, data: dict) -> dict[str, str]:
        """Document the execute rule at the boundary where callers use it.

        The caller gets one stable method even when this component needs fallbacks or provider-specific
        handling.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                {"enabled": True}
        """
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
        if export_cfg.get("claims_csv", True):
            paths["claims_csv"] = _write_claims(report, reports_dir, stem)
        if export_cfg.get("narratives_csv", True):
            paths["narratives_csv"] = _write_narratives(report, reports_dir, stem)
        if export_cfg.get("run_summary_json", True):
            summary_paths = dict(paths)
            html_path = resolve_html_report_path(report)
            if html_path is not None:
                summary_paths["html_report"] = str(html_path)
            paths["run_summary_json"] = _write_run_summary(
                report, config, summary_paths, reports_dir, stem
            )
        return paths
