"""commands/report.py — Re-render an HTML report from a saved report file.

Intended as the override path when an operator wants to replace Compiled
Synthesis, Opportunity Analysis, or Final Summary after research has already
emitted the report JSON.

Usage:
    srp report --report PATH [--compiled-synthesis FILE] [--opportunity-analysis FILE]
               [--final-summary FILE] [--out PATH]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from social_research_probe.config import load_active_config
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.exit_codes import ExitCode
from social_research_probe.utils.core.report import unwrap_report
from social_research_probe.utils.display.service_log import service_log_sync


def _load_and_validate_report(report_path: str) -> dict:
    """Load report JSON and validate structure."""
    try:
        payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read report file: {exc}") from exc
    report = unwrap_report(payload)
    if not isinstance(report, dict):
        raise ValidationError("report file must contain a JSON object")
    return report


def _apply_text_overrides(
    report: dict,
    compiled_synthesis_path: str | None,
    opportunity_analysis_path: str | None,
    final_summary_path: str | None,
) -> dict:
    """Apply text file overrides to report."""
    rendered_report = dict(report)
    for key, path in (
        ("compiled_synthesis", compiled_synthesis_path),
        ("opportunity_analysis", opportunity_analysis_path),
        ("report_summary", final_summary_path),
    ):
        text = _read_text_file(path)
        if text is not None:
            rendered_report[key] = text
    return rendered_report


def _prepare_tts_setup(
    report: dict, out_path: str | None, cfg_logs: bool
) -> tuple[list, str | None, dict]:
    """Fetch voicebox profiles and prepare audio if enabled. Returns (profiles, profile_name, audio_sources)."""
    from social_research_probe.technologies.report_render.html.raw_html.youtube import (
        _audio_report_enabled,
        _fetch_voicebox_profiles,
        _prepare_voiceover_audios,
        _select_voicebox_profile,
        _voicebox_api_base,
        _voicebox_default_profile_name,
        _write_discovered_voicebox_profile_names,
    )

    cfg = load_active_config()
    api_base = _voicebox_api_base()
    tts_profiles: list[dict[str, str]] = []
    selected_profile_name = None
    prepared_audio_sources: dict[str, str] = {}

    if cfg.technology_enabled("voicebox"):
        with service_log_sync("voicebox_profiles", report=report, cfg_logs_enabled=cfg_logs):
            tts_profiles = _fetch_voicebox_profiles(api_base)
        _write_discovered_voicebox_profile_names(tts_profiles)
        selected_profile = _select_voicebox_profile(
            tts_profiles,
            tts_profile_name=_voicebox_default_profile_name(),
        )
        selected_profile_name = selected_profile["name"] if selected_profile is not None else None

        if out_path and _audio_report_enabled():
            with service_log_sync("voicebox_audio", report=report, cfg_logs_enabled=cfg_logs):
                prepared_audio_sources = _prepare_voiceover_audios(
                    report,
                    Path(out_path),
                    tts_api_base=api_base,
                    tts_profiles=tts_profiles,
                    tts_profile_name=selected_profile_name,
                )

    return tts_profiles, selected_profile_name, prepared_audio_sources


def _render_and_output_html(
    report: dict,
    charts_dir: Path | None,
    out_path: str | None,
    tts_profiles: list,
    selected_profile_name: str | None,
    prepared_audio_sources: dict,
    tts_api_base: str,
) -> None:
    """Render HTML and write to file or stdout."""
    from social_research_probe.technologies.report_render.html.raw_html.youtube import (
        render_html,
        serve_report_command,
    )

    prepared_audio_src = prepared_audio_sources.get(selected_profile_name or "")
    prepared_audio_profile_name = selected_profile_name if prepared_audio_src else None

    html_content = render_html(
        report,
        charts_dir=charts_dir,
        tts_api_base=tts_api_base,
        tts_profile_name=selected_profile_name,
        tts_profiles=tts_profiles,
        prepared_audio_src=prepared_audio_src,
        prepared_audio_profile_name=prepared_audio_profile_name,
        prepared_audio_sources=prepared_audio_sources,
    )

    if out_path:
        dest = Path(out_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_content, encoding="utf-8")
        print(f"[srp] Serve report: {serve_report_command(dest)}", file=sys.stderr)
    else:
        sys.stdout.write(html_content)


def run(
    report_path: str,
    compiled_synthesis_path: str | None,
    opportunity_analysis_path: str | None,
    final_summary_path: str | None,
    out_path: str | None,
) -> int:
    """Read a report JSON file and write (or rewrite) its HTML report."""
    from social_research_probe.technologies.report_render.html.raw_html.youtube import (
        _technology_logs_enabled,
        _voicebox_api_base,
    )

    report = _load_and_validate_report(report_path)
    cfg = load_active_config()
    platform = str(report.get("platform", "youtube"))
    if out_path and (not cfg.stage_enabled(platform, "report") or not cfg.service_enabled("html")):
        raise ValidationError("HTML report generation is disabled by config")

    rendered_report = _apply_text_overrides(
        report,
        compiled_synthesis_path,
        opportunity_analysis_path,
        final_summary_path,
    )

    report_parent = Path(report_path).parent
    charts_dir = report_parent / "charts"
    charts_dir_arg = charts_dir if charts_dir.is_dir() else None

    cfg_logs = _technology_logs_enabled()
    tts_api_base = _voicebox_api_base()
    tts_profiles, selected_profile_name, prepared_audio_sources = _prepare_tts_setup(
        rendered_report, out_path, cfg_logs
    )

    _render_and_output_html(
        rendered_report,
        charts_dir_arg,
        out_path,
        tts_profiles,
        selected_profile_name,
        prepared_audio_sources,
        tts_api_base,
    )
    return ExitCode.SUCCESS


def _read_text_file(path: str | None) -> str | None:
    """Read a text file's content or return None if path is None."""
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8").strip() or None
    except OSError as exc:
        raise ValidationError(f"cannot read file {path!r}: {exc}") from exc
