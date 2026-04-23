"""commands/report.py — Re-render an HTML report from a saved packet file.

Intended as the override path when an operator wants to replace Compiled
Synthesis, Opportunity Analysis, or Final Summary after research has already
emitted the packet JSON.

Usage:
    srp report --packet PATH [--compiled-synthesis FILE] [--opportunity-analysis FILE]
               [--final-summary FILE] [--out PATH]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from social_research_probe.config import Config, resolve_data_dir
from social_research_probe.errors import ValidationError
from social_research_probe.packet import unwrap_packet
from social_research_probe.utils.service_log import service_log_sync


def run(
    packet_path: str,
    compiled_synthesis_path: str | None,
    opportunity_analysis_path: str | None,
    final_summary_path: str | None,
    out_path: str | None,
    *,
    data_dir: Path | None = None,
) -> int:
    """Read a packet JSON file and write (or rewrite) its HTML report.

    Args:
        packet_path: Path to the packet JSON file.
        compiled_synthesis_path: Optional path to a file containing Compiled Synthesis text.
        opportunity_analysis_path: Optional path to a file containing Opportunity Analysis text.
        final_summary_path: Optional path to a file containing Final Summary text.
        out_path: Destination HTML path. If None, prints to stdout.

    Returns:
        Exit code (0 on success).

    Raises:
        ValidationError: If the packet file cannot be read or is invalid JSON.
    """
    try:
        payload = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read packet file: {exc}") from exc
    packet = unwrap_packet(payload)
    if not isinstance(packet, dict):
        raise ValidationError("packet file must contain a JSON object")

    compiled_synthesis = _read_text_file(compiled_synthesis_path)
    opportunity_analysis = _read_text_file(opportunity_analysis_path)
    final_summary = _read_text_file(final_summary_path)

    from social_research_probe.render.html import (
        _fetch_voicebox_profiles,
        _prepare_voiceover_audios,
        _select_voicebox_profile,
        _voicebox_api_base,
        _voicebox_default_profile_name,
        _write_discovered_voicebox_profile_names,
        render_html,
        serve_report_command,
    )

    data_dir = data_dir or resolve_data_dir(None)
    cfg = Config.load(data_dir)
    if out_path and (not cfg.stage_enabled("report") or not cfg.service_enabled("html_report")):
        raise ValidationError("HTML report generation is disabled by config")

    # Resolve charts_dir relative to the packet file's parent directory if
    # the standard layout is present (packet file next to a charts/ sibling).
    packet_parent = Path(packet_path).parent
    charts_dir = packet_parent / "charts"
    charts_dir_arg = charts_dir if charts_dir.is_dir() else None

    rendered_packet = dict(packet)
    if compiled_synthesis is not None:
        rendered_packet["compiled_synthesis"] = compiled_synthesis
    if opportunity_analysis is not None:
        rendered_packet["opportunity_analysis"] = opportunity_analysis
    if final_summary is not None:
        rendered_packet["report_summary"] = final_summary

    cfg_logs = _technology_logs_enabled(data_dir)
    api_base = _voicebox_api_base()
    tts_profiles: list[dict[str, str]] = []
    selected_profile = None
    if cfg.technology_enabled("voicebox"):
        with service_log_sync(
            "voicebox_profiles", packet=rendered_packet, cfg_logs_enabled=cfg_logs
        ):
            tts_profiles = _fetch_voicebox_profiles(api_base)
        _write_discovered_voicebox_profile_names(data_dir, tts_profiles)
        selected_profile = _select_voicebox_profile(
            tts_profiles,
            tts_profile_name=_voicebox_default_profile_name(data_dir),
        )
    selected_profile_name = selected_profile["name"] if selected_profile is not None else None
    prepared_audio_src = None
    prepared_audio_profile_name = None
    prepared_audio_sources: dict[str, str] = {}
    if out_path and _audio_report_enabled(data_dir) and cfg.technology_enabled("voicebox"):
        with service_log_sync("voicebox_audio", packet=rendered_packet, cfg_logs_enabled=cfg_logs):
            prepared_audio_sources = _prepare_voiceover_audios(
                rendered_packet,
                Path(out_path),
                tts_api_base=api_base,
                tts_profiles=tts_profiles,
                tts_profile_name=selected_profile_name,
            )
        prepared_audio_src = prepared_audio_sources.get(selected_profile_name or "", None)
        prepared_audio_profile_name = selected_profile_name if prepared_audio_src else None

    html_content = render_html(
        rendered_packet,
        charts_dir=charts_dir_arg,
        data_dir=data_dir,
        tts_api_base=api_base,
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
    return 0


def _audio_report_enabled(data_dir: Path | None = None) -> bool:
    """Return whether pre-rendered Voicebox audio is enabled in active config."""
    try:
        cfg = Config.load(data_dir or resolve_data_dir(None))
        return cfg.stage_enabled("report") and cfg.service_enabled("audio_report")
    except Exception:
        return True


def _technology_logs_enabled(data_dir: Path | None = None) -> bool:
    """Return whether technology lifecycle logs are enabled in active config."""
    try:
        return bool(
            Config.load(data_dir or resolve_data_dir(None)).debug.get(
                "technology_logs_enabled", False
            )
        )
    except Exception:
        return False


def _read_text_file(path: str | None) -> str | None:
    """Read a text file's content or return None if path is None."""
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8").strip() or None
    except OSError as exc:
        raise ValidationError(f"cannot read file {path!r}: {exc}") from exc
