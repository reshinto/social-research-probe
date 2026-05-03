"""HTML report renderer for srp research reports.

Produces a single self-contained HTML file with embedded chart images
(base64 PNG), a sticky TOC, and text-to-speech controls that prefer
Voicebox while falling back to the browser's system voices.
The output is identical regardless of whether research was triggered by
the skill or the CLI — both call write_html_report() after obtaining a
ResearchReport.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shlex
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from social_research_probe.config import load_active_config
from social_research_probe.technologies.report_render.html.raw_html._assets import (
    CSS_STYLES,
    TTS_SCRIPT,
)
from social_research_probe.technologies.report_render.html.raw_html._sections import (
    section_1_topic_purpose,
    section_2_platform,
    section_3_top_items,
    section_4_platform_engagement,
    section_5_source_validation,
    section_6_evidence,
    section_7_statistics,
    section_8_charts,
    section_9_warnings,
    section_10_synthesis,
    section_11_opportunity,
    section_12_summary,
    section_narratives,
)
from social_research_probe.utils.core.types import ResearchReport
from social_research_probe.utils.display.service_log import service_log_sync
from social_research_probe.utils.report.formatter import (
    resolve_report_summary,
)

_IMPORTED_LOAD_ACTIVE_CONFIG = load_active_config

_SECTIONS = [
    ("s1", "1. Topic &amp; Purpose"),
    ("s2", "2. Platform"),
    ("s3", "3. Top Items"),
    ("s4", "4. Platform Signals"),
    ("s5", "5. Source Validation"),
    ("s6", "6. Evidence"),
    ("s7", "7. Statistics"),
    ("s8", "8. Charts"),
    ("s9", "9. Warnings"),
    ("narratives", "10. Narrative Clusters"),
    ("compiled-synthesis", "11. Compiled Synthesis"),
    ("opportunity-analysis", "12. Opportunity Analysis"),
    ("final-summary", "13. Final Summary"),
]


def _default_voicebox_api_base() -> str:
    """Get default Voicebox API base from config.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _default_voicebox_api_base()
        Output:
            "http://127.0.0.1:5050"
    """
    from social_research_probe.config import load_active_config

    return load_active_config().voicebox["api_base"]


_VOICEBOX_PROFILE_NAMES_FILENAME = "voicebox_profiles.json"


def render_html(
    report: ResearchReport,
    charts_dir: Path | None = None,
    *,
    tts_api_base: str | None = None,
    tts_profile_name: str | None = None,
    tts_profiles: list[dict[str, str]] | None = None,
    embed_voicebox_profiles: bool = False,
    prepared_audio_src: str | None = None,
    prepared_audio_profile_name: str | None = None,
    prepared_audio_sources: dict[str, str] | None = None,
) -> str:
    """Render a complete self-contained HTML report for a research report.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        charts_dir: Filesystem location used to read, write, or resolve project data.
        tts_api_base: Voicebox or provider API base URL used for outbound requests.
        tts_profile_name: Voice or runner profile selected for the current operation.
        tts_profiles: Voice or runner profile selected for the current operation.
        embed_voicebox_profiles: Voice or runner profile selected for the current operation.
        prepared_audio_src: Prepared narration audio filename or profile-to-file map for the HTML
                            report.
        prepared_audio_profile_name: Voice or runner profile selected for the current operation.
        prepared_audio_sources: Prepared narration audio filename or profile-to-file map for the
                                HTML report.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            render_html(
                report={"topic": "AI safety", "items_top_n": []},
                charts_dir=Path(".skill-data"),
                tts_api_base="http://127.0.0.1:5050",
                tts_profile_name={"name": "Alloy", "id": "alloy"},
                tts_profiles={"name": "Alloy", "id": "alloy"},
                embed_voicebox_profiles={"name": "Alloy", "id": "alloy"},
                prepared_audio_src="report.voicebox.Alloy.wav",
                prepared_audio_profile_name={"name": "Alloy", "id": "alloy"},
                prepared_audio_sources={"Alloy": "report.voicebox.Alloy.wav"},
            )
        Output:
            "<section>Summary</section>"
    """
    api_base = tts_api_base or _voicebox_api_base()
    selected_profile_name = tts_profile_name or _voicebox_default_profile_name()
    if tts_profiles is None:
        tts_profiles = _fetch_voicebox_profiles(api_base) if embed_voicebox_profiles else []
        if embed_voicebox_profiles:
            _write_discovered_voicebox_profile_names(tts_profiles)
    selected_profile = _select_voicebox_profile(
        tts_profiles,
        tts_profile_name=selected_profile_name,
    )
    if selected_profile is not None:
        selected_profile_name = selected_profile["name"]
    section_bodies = [
        section_1_topic_purpose(report),
        section_2_platform(report),
        section_3_top_items(report),
        section_4_platform_engagement(report),
        section_5_source_validation(report),
        section_6_evidence(report),
        section_7_statistics(report),
        section_8_charts(report, charts_dir),
        section_9_warnings(report),
        section_narratives(report),
        section_10_synthesis(report.get("compiled_synthesis")),
        section_11_opportunity(report.get("opportunity_analysis")),
        section_12_summary(resolve_report_summary(report)),
    ]
    body_html = _build_body(report, section_bodies)
    toc_html = _build_toc()
    return _page_shell(
        report,
        toc_html,
        body_html,
        tts_api_base=api_base,
        tts_profiles=tts_profiles,
        tts_profile_name=selected_profile_name,
        prepared_audio_src=prepared_audio_src,
        prepared_audio_profile_name=prepared_audio_profile_name,
        prepared_audio_sources=prepared_audio_sources or {},
    )


def write_html_report(
    report: ResearchReport,
    *,
    prepare_voicebox_audio: bool | None = None,
) -> Path:
    """Write an HTML report to data_dir/reports/ and return its path.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
                prepare_voicebox_audio: Flag indicating whether Voicebox narration should be pre-rendered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            write_html_report(
                report={"topic": "AI safety", "items_top_n": []},
                prepare_voicebox_audio="AI safety",
            )
        Output:
            None
    """
    cfg = load_active_config()
    data_dir = cfg.data_dir
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^\w-]", "-", report["topic"].lower())[:40].strip("-")
    platform = report.get("platform", "unknown")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = reports_dir / f"{slug}-{platform}-{ts}.html"

    cfg_logs = _technology_logs_enabled()
    api_base = _voicebox_api_base()
    tts_profiles: list[dict[str, str]] = []
    selected_profile = None
    if cfg.technology_enabled("voicebox"):
        with service_log_sync("voicebox_profiles", report=report, cfg_logs_enabled=cfg_logs):
            tts_profiles = _fetch_voicebox_profiles(api_base)
        _write_discovered_voicebox_profile_names(tts_profiles)
        selected_profile = _select_voicebox_profile(
            tts_profiles,
            tts_profile_name=_voicebox_default_profile_name(),
        )
    selected_profile_name = selected_profile["name"] if selected_profile is not None else None
    audio_enabled = (
        _audio_report_enabled() if prepare_voicebox_audio is None else bool(prepare_voicebox_audio)
    )
    prepared_audio_sources: dict[str, str] = {}
    if audio_enabled and cfg.technology_enabled("voicebox"):
        with service_log_sync("voicebox_audio", report=report, cfg_logs_enabled=cfg_logs):
            prepared_audio_sources = _prepare_voiceover_audios(
                report,
                out_path,
                tts_api_base=api_base,
                tts_profiles=tts_profiles,
                tts_profile_name=selected_profile_name,
            )
    prepared_audio_src = prepared_audio_sources.get(selected_profile_name or "", None)
    prepared_audio_profile_name = selected_profile_name if prepared_audio_src else None
    html_content = render_html(
        report,
        charts_dir=data_dir / "charts",
        tts_api_base=api_base,
        tts_profile_name=selected_profile_name,
        tts_profiles=tts_profiles,
        prepared_audio_src=prepared_audio_src,
        prepared_audio_profile_name=prepared_audio_profile_name,
        prepared_audio_sources=prepared_audio_sources,
    )
    out_path.write_text(html_content, encoding="utf-8")
    print(f"[srp] Serve report: {serve_report_command(out_path)}", file=sys.stderr)
    return out_path


def _build_toc() -> str:
    """Build the sidebar table-of-contents HTML.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _build_toc()
        Output:
            "AI safety"
    """
    links = "".join(f'<a href="#{sid}">{label}</a>' for sid, label in _SECTIONS)
    return f"<h2>Contents</h2>{links}"


def _build_body(report: ResearchReport, section_bodies: list[str]) -> str:
    """Build the <main> report body from section bodies.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        section_bodies: HTML, caption, metric, or report text being formatted for the final report.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _build_body(
                report={"topic": "AI safety", "items_top_n": []},
                section_bodies="<section>Summary</section>",
            )
        Output:
            "AI safety"
    """
    topic_esc = html.escape(report["topic"])
    platform_esc = html.escape(report.get("platform", ""))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        f'<h1 class="report-title">{topic_esc}</h1>',
        f'<p class="report-meta">Platform: {platform_esc} &nbsp;·&nbsp; Generated: {timestamp}</p>',
    ]
    for (sid, label), body in zip(_SECTIONS, section_bodies, strict=True):
        parts.append(f'<section id="{sid}"><h2>{label}</h2>{body}</section>')
    return "\n".join(parts)


def _voicebox_api_base() -> str:
    """Return the Voicebox base URL used by the HTML report runtime.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _voicebox_api_base()
        Output:
            "http://127.0.0.1:5050"
    """
    return os.environ.get("SRP_VOICEBOX_API_BASE", _default_voicebox_api_base()).rstrip("/")


def _display_path(path: Path) -> str:
    """Return *path* as a user-facing path, preferring ``~/`` under home.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _display_path(
                path=Path("report.html"),
            )
        Output:
            "AI safety"
    """
    resolved = path.resolve()
    home = Path.home().resolve()
    try:
        relative = resolved.relative_to(home)
    except ValueError:
        return str(resolved)
    return f"~/{relative.as_posix()}"


def serve_report_command(report_path: Path) -> str:
    """Return the recommended local command to open *report_path* via HTTP.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            serve_report_command(
                report_path=Path("report.html"),
            )
        Output:
            "AI safety"
    """
    return f"srp serve-report --report {shlex.quote(_display_path(report_path))}"


def _voicebox_default_profile_name() -> str:
    """Return the configured preferred Voicebox profile name.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _voicebox_default_profile_name()
        Output:
            "AI safety"
    """
    try:
        value = str(load_active_config().voicebox.get("default_profile_name", "")).strip()
    except Exception:
        value = ""
    return value or "Jarvis"


def _voicebox_profile_names_path() -> Path:
    """Return the discovered Voicebox profile-name cache path.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _voicebox_profile_names_path()
        Output:
            Path("report.html")
    """
    return load_active_config().data_dir / _VOICEBOX_PROFILE_NAMES_FILENAME


def _normalize_voicebox_profile_name(name: str) -> str:
    """Normalize a Voicebox profile name for matching and deduplication.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        name: Registry, config, or CLI name used to select the matching project value.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _normalize_voicebox_profile_name(
                name="AI safety",
            )
        Output:
            "AI safety"
    """
    return re.sub(r"\s+", " ", str(name or "").strip()).casefold()


def _dedupe_voicebox_profile_name(raw_name: str, seen_names: set[str]) -> str:
    """Return a readable, unique profile name without leaking profile IDs.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        raw_name: Profile name before filesystem-safe normalization.
        seen_names: Profile names already used while making audio filenames unique.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _dedupe_voicebox_profile_name(
                raw_name="AI safety",
                seen_names="AI safety",
            )
        Output:
            "AI safety"
    """
    base_name = str(raw_name or "").strip() or "Voicebox Profile"
    candidate = base_name
    suffix = 2
    while _normalize_voicebox_profile_name(candidate) in seen_names:
        candidate = f"{base_name} ({suffix})"
        suffix += 1
    seen_names.add(_normalize_voicebox_profile_name(candidate))
    return candidate


def _write_discovered_voicebox_profile_names(tts_profiles: list[dict[str, str]]) -> None:
    """Overwrite the cached Voicebox profile-name list when profiles were found.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        tts_profiles: Voice or runner profile selected for the current operation.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_discovered_voicebox_profile_names(
                tts_profiles={"name": "Alloy", "id": "alloy"},
            )
        Output:
            None
    """
    if not tts_profiles:
        return
    profile_names: list[str] = []
    seen_names: set[str] = set()
    for profile in tts_profiles:
        name = str(profile.get("name", "")).strip()
        normalized = _normalize_voicebox_profile_name(name)
        if not normalized or normalized in seen_names:
            continue
        profile_names.append(name)
        seen_names.add(normalized)
    if not profile_names:
        return
    out_path = _voicebox_profile_names_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profile_names, ensure_ascii=True, indent=2), encoding="utf-8")


def _profile_lookup_name(profile: dict[str, str]) -> str:
    """Return the normalized lookup name for one Voicebox profile.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        profile: Voice or runner profile selected for the current operation.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _profile_lookup_name(
                profile={"name": "Alloy", "id": "alloy"},
            )
        Output:
            "AI safety"
    """
    return _normalize_voicebox_profile_name(profile.get("name", ""))


def _fetch_voicebox_profiles(api_base: str) -> list[dict[str, str]]:
    """Fetch Voicebox profiles from *api_base* and normalize them for the UI.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        api_base: Voicebox or provider API base URL used for outbound requests.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _fetch_voicebox_profiles(
                api_base="http://127.0.0.1:5050",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    try:
        with urllib.request.urlopen(f"{api_base}/profiles", timeout=1.5) as resp:
            payload = json.load(resp)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        return []

    if isinstance(payload, list):
        raw_profiles = payload
    elif isinstance(payload, dict):
        raw_profiles = payload.get("profiles", [])
    else:
        return []

    profiles: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for raw in raw_profiles:
        if not isinstance(raw, dict):
            continue
        profile_id = str(raw.get("id", "")).strip()
        if not profile_id or profile_id in seen_ids:
            continue
        name = _dedupe_voicebox_profile_name(str(raw.get("name") or ""), seen_names)
        profiles.append({"id": profile_id, "name": name})
        seen_ids.add(profile_id)
    return profiles


def _audio_report_enabled() -> bool:
    """Return whether pre-rendered Voicebox audio is enabled (technology gate only).

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _audio_report_enabled()
        Output:
            True
    """
    try:
        return load_active_config().technology_enabled("voicebox")
    except Exception:
        return True


def _technology_logs_enabled() -> bool:
    """Return whether technology lifecycle logs are enabled.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _technology_logs_enabled()
        Output:
            True
    """
    try:
        if load_active_config is not _IMPORTED_LOAD_ACTIVE_CONFIG:
            cfg = load_active_config()
        else:
            from social_research_probe import config as srp_config

            cfg = srp_config.load_active_config()
        return bool(cfg.debug.get("technology_logs_enabled", False))
    except Exception:
        return False


def _build_tts_voice_options(
    tts_profiles: list[dict[str, str]],
    selected_profile_name: str | None,
) -> str:
    """Build the Voicebox profile <option> markup for the toolbar dropdown.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        tts_profiles: Voice or runner profile selected for the current operation.
        selected_profile_name: Voice or runner profile selected for the current operation.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _build_tts_voice_options(
                tts_profiles={"name": "Alloy", "id": "alloy"},
                selected_profile_name={"name": "Alloy", "id": "alloy"},
            )
        Output:
            "AI safety"
    """
    if not tts_profiles:
        return '<option value="">Choose voice</option>'

    selected_profile = _select_voicebox_profile(
        tts_profiles,
        tts_profile_name=selected_profile_name,
    )
    selected_name = (
        selected_profile["name"] if selected_profile is not None else tts_profiles[0]["name"]
    )
    options: list[str] = []
    for profile in tts_profiles:
        attrs = ' selected="selected"' if profile["name"] == selected_name else ""
        options.append(
            f'<option value="voicebox::{html.escape(profile["name"], quote=True)}" '
            f'data-source="voicebox" data-voice-name="{html.escape(profile["name"], quote=True)}"{attrs}>'
            f"{html.escape(profile['name'])}"
            "</option>"
        )
    return f'<optgroup label="Voicebox">{"".join(options)}</optgroup>'


def _select_voicebox_profile(
    tts_profiles: list[dict[str, str]],
    *,
    tts_profile_name: str | None,
) -> dict[str, str] | None:
    """Return the preferred Voicebox profile for the report.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        tts_profiles: Voice or runner profile selected for the current operation.
        tts_profile_name: Voice or runner profile selected for the current operation.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _select_voicebox_profile(
                tts_profiles={"name": "Alloy", "id": "alloy"},
                tts_profile_name={"name": "Alloy", "id": "alloy"},
            )
        Output:
            {"enabled": True}
    """
    if not tts_profiles:
        return None
    preferred_name = _normalize_voicebox_profile_name(tts_profile_name or "")
    if preferred_name:
        for profile in tts_profiles:
            if _profile_lookup_name(profile) == preferred_name:
                return profile
    return tts_profiles[0]


@lru_cache(maxsize=128)
def _markdown_to_voiceover_text(text: str) -> str:
    """Collapse markdown-ish synthesis text into plain narration text.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _markdown_to_voiceover_text(
                text="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    cleaned = text.replace("\r\n", "\n")
    cleaned = re.sub(r"```.+?```", " ", cleaned, flags=re.S)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s+", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.M)
    cleaned = re.sub(r"[*_~]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_voiceover_text(report: ResearchReport) -> str | None:
    """Return the summary-only narration text used for prepared audio.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            build_voiceover_text(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    sections: list[str] = []
    for label, key in (
        ("Compiled synthesis", "compiled_synthesis"),
        ("Opportunity analysis", "opportunity_analysis"),
    ):
        raw = str(report.get(key, "") or "").strip()
        if not raw:
            continue
        plain = _markdown_to_voiceover_text(raw)
        if plain:
            sections.append(f"{label}. {plain}")
    final_summary = resolve_report_summary(report) or ""
    final_summary_plain = _markdown_to_voiceover_text(final_summary) if final_summary else ""
    if final_summary_plain:
        sections.append(f"Final summary. {final_summary_plain}")
    if not sections:
        return None
    return " ".join(sections)


def _prepare_voiceover_audio(
    report: ResearchReport,
    report_path: Path,
    *,
    tts_api_base: str,
    tts_profile: dict[str, str] | None,
) -> tuple[str | None, str | None]:
    """Pre-render summary audio for *report* and return (filename, profile_name).

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        report_path: Filesystem location used to read, write, or resolve project data.
        tts_api_base: Voicebox or provider API base URL used for outbound requests.
        tts_profile: Voice or runner profile selected for the current operation.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _prepare_voiceover_audio(
                report={"topic": "AI safety", "items_top_n": []},
                report_path=Path("report.html"),
                tts_api_base="http://127.0.0.1:5050",
                tts_profile={"name": "Alloy", "id": "alloy"},
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    if not tts_profile:
        return None, None
    text = build_voiceover_text(report)
    if not text:
        return None, None

    from social_research_probe.technologies.tts.voicebox import write_audio

    audio_base = report_path.with_name(report_path.stem + ".voicebox")
    try:
        audio_path = write_audio(
            text,
            out_base=audio_base,
            api_base=tts_api_base,
            profile_id=tts_profile["id"],
        )
    except RuntimeError as exc:
        print(f"[srp] Voicebox audio pre-render skipped: {exc}", file=sys.stderr)
        return None, None
    return audio_path.name, tts_profile["name"]


def _prepare_voiceover_audios(
    report: ResearchReport,
    report_path: Path,
    *,
    tts_api_base: str,
    tts_profiles: list[dict[str, str]],
    tts_profile_name: str | None,
) -> dict[str, str]:
    """Pre-render summary audio for all known Voicebox profiles concurrently.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        report_path: Filesystem location used to read, write, or resolve project data.
        tts_api_base: Voicebox or provider API base URL used for outbound requests.
        tts_profiles: Voice or runner profile selected for the current operation.
        tts_profile_name: Voice or runner profile selected for the current operation.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _prepare_voiceover_audios(
                report={"topic": "AI safety", "items_top_n": []},
                report_path=Path("report.html"),
                tts_api_base="http://127.0.0.1:5050",
                tts_profiles={"name": "Alloy", "id": "alloy"},
                tts_profile_name={"name": "Alloy", "id": "alloy"},
            )
        Output:
            {"enabled": True}
    """
    text = build_voiceover_text(report)
    if not text or not tts_profiles:
        return {}

    prepared: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(tts_profiles)) as pool:
        futures = {
            pool.submit(
                _prepare_voiceover_audio_for_profile,
                text=text,
                report_path=report_path,
                tts_api_base=tts_api_base,
                profile=profile,
            ): profile
            for profile in tts_profiles
        }
        for future in as_completed(futures):
            profile = futures[future]
            try:
                finished_profile_name, audio_name = future.result()
            except RuntimeError as exc:
                print(
                    f"[srp] Voicebox audio pre-render skipped for profile {profile['name']}: {exc}",
                    file=sys.stderr,
                )
                continue
            prepared[finished_profile_name] = audio_name
    return prepared


def _prepare_voiceover_audio_for_profile(
    *,
    text: str,
    report_path: Path,
    tts_api_base: str,
    profile: dict[str, str],
) -> tuple[str, str]:
    """Write one profile-specific narration file so the report can switch voices offline.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        report_path: Filesystem location used to read, write, or resolve project data.
        tts_api_base: Voicebox or provider API base URL used for outbound requests.
        profile: Voice or runner profile selected for the current operation.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _prepare_voiceover_audio_for_profile(
                text="This tool reduces latency by 30%.",
                report_path=Path("report.html"),
                tts_api_base="http://127.0.0.1:5050",
                profile={"name": "Alloy", "id": "alloy"},
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    from social_research_probe.technologies.tts.voicebox import write_audio

    audio_base = _prepared_audio_base(report_path, profile["name"])
    audio_path = write_audio(
        text,
        out_base=audio_base,
        api_base=tts_api_base,
        profile_id=profile["id"],
    )
    return profile["name"], audio_path.name


def _prepared_audio_base(report_path: Path, profile_name: str) -> Path:
    """Return the output base path for one prepared profile audio file.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report_path: Filesystem location used to read, write, or resolve project data.
        profile_name: Voice or runner profile selected for the current operation.

    Returns:
        Resolved filesystem path, or None when the optional path is intentionally absent.

    Examples:
        Input:
            _prepared_audio_base(
                report_path=Path("report.html"),
                profile_name={"name": "Alloy", "id": "alloy"},
            )
        Output:
            Path("report.html")
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", profile_name).strip("-").lower()[:24] or "voice"
    digest = hashlib.sha1(profile_name.encode("utf-8")).hexdigest()[:8]
    name = f"{report_path.stem}.voicebox.{slug}-{digest}"
    return report_path.with_name(name)


def _page_shell(
    report: ResearchReport,
    toc_html: str,
    body_html: str,
    *,
    tts_api_base: str,
    tts_profiles: list[dict[str, str]],
    tts_profile_name: str | None,
    prepared_audio_src: str | None,
    prepared_audio_profile_name: str | None,
    prepared_audio_sources: dict[str, str],
) -> str:
    """Assemble the complete HTML document from its parts.

    Report rendering has to turn loose research dictionaries into deterministic files, so each
    formatting rule is isolated and easy to review.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.
        toc_html: HTML, caption, metric, or report text being formatted for the final report.
        body_html: HTML, caption, metric, or report text being formatted for the final report.
        tts_api_base: Voicebox or provider API base URL used for outbound requests.
        tts_profiles: Voice or runner profile selected for the current operation.
        tts_profile_name: Voice or runner profile selected for the current operation.
        prepared_audio_src: Prepared narration audio filename or profile-to-file map for the HTML
                            report.
        prepared_audio_profile_name: Voice or runner profile selected for the current operation.
        prepared_audio_sources: Prepared narration audio filename or profile-to-file map for the
                                HTML report.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _page_shell(
                report={"topic": "AI safety", "items_top_n": []},
                toc_html="<nav>Contents</nav>",
                body_html="<section>Summary</section>",
                tts_api_base="http://127.0.0.1:5050",
                tts_profiles={"name": "Alloy", "id": "alloy"},
                tts_profile_name={"name": "Alloy", "id": "alloy"},
                prepared_audio_src="report.voicebox.Alloy.wav",
                prepared_audio_profile_name={"name": "Alloy", "id": "alloy"},
                prepared_audio_sources={"Alloy": "report.voicebox.Alloy.wav"},
            )
        Output:
            "AI safety"
    """
    title = html.escape(f"Research Report: {report['topic']}")
    voice_options = _build_tts_voice_options(tts_profiles, tts_profile_name)
    default_profile_attr = html.escape(tts_profile_name or "", quote=True)
    api_base_attr = html.escape(tts_api_base, quote=True)
    prepared_audio_attr = html.escape(prepared_audio_src or "", quote=True)
    prepared_profile_attr = html.escape(prepared_audio_profile_name or "", quote=True)
    prepared_audio_map = html.escape(
        json.dumps(prepared_audio_sources, ensure_ascii=True, sort_keys=True),
        quote=False,
    )
    tts_bar = (
        f'<div id="tts-bar" data-api-base="{api_base_attr}" '
        f'data-prepared-audio-src="{prepared_audio_attr}" '
        f'data-prepared-profile-name="{prepared_profile_attr}">'
        '<button id="tts-play">\u25b6 Play</button>'
        '<button id="tts-pause" disabled>\u23f8 Pause</button>'
        '<button id="tts-stop" disabled>\u23f9 Stop</button>'
        '<label for="tts-rate" style="font-size:.8rem;opacity:.7">Speed</label>'
        '<select id="tts-rate">'
        '<option value="0.75">0.75\u00d7</option>'
        '<option value="1" selected>1\u00d7</option>'
        '<option value="1.25">1.25\u00d7</option>'
        '<option value="1.5">1.5\u00d7</option>'
        '<option value="2">2\u00d7</option>'
        "</select>"
        '<label for="tts-voice" style="font-size:.8rem;opacity:.7">Voice</label>'
        f'<select id="tts-voice" data-default-profile-name="{default_profile_attr}">{voice_options}</select>'
        '<button id="tts-refresh" type="button">Refresh Voices</button>'
        '<span id="tts-label"></span>'
        "</div>"
        '<audio id="tts-audio" preload="none"></audio>'
        f'<script id="tts-prepared-audio-map" type="application/json">{prepared_audio_map}</script>'
    )
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{title}</title>\n"
        f"<style>{CSS_STYLES}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{tts_bar}\n"
        '<div id="layout">\n'
        f'<nav id="toc">{toc_html}</nav>\n'
        f'<main id="report-body">{body_html}</main>\n'
        "</div>\n"
        f"<script>{TTS_SCRIPT}</script>\n"
        "</body>\n"
        "</html>"
    )
