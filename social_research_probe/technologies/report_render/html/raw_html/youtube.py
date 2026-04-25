"""HTML report renderer for srp research packets.

Produces a single self-contained HTML file with embedded chart images
(base64 PNG), a sticky TOC, and text-to-speech controls that prefer
Voicebox while falling back to the browser's system voices.
The output is identical regardless of whether research was triggered by
the skill or the CLI — both call write_html_report() after obtaining a
ResearchPacket.
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
from social_research_probe.services.synthesizing.formatter import resolve_report_summary
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
)
from social_research_probe.utils.core.types import ResearchPacket
from social_research_probe.utils.display.service_log import service_log_sync

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
    ("compiled-synthesis", "10. Compiled Synthesis"),
    ("opportunity-analysis", "11. Opportunity Analysis"),
    ("final-summary", "12. Final Summary"),
]

def _default_voicebox_api_base() -> str:
    """Get default Voicebox API base from config."""
    from social_research_probe.config import load_active_config
    return load_active_config().voicebox["api_base"]
_VOICEBOX_PROFILE_NAMES_FILENAME = "voicebox_profiles.json"


def render_html(
    packet: ResearchPacket,
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
    """Render a complete self-contained HTML report for a research packet.

    Args:
        packet: The research packet produced by pipeline.run_research().
        charts_dir: Directory containing chart PNGs to embed. None → skip images.
        tts_api_base: Voicebox HTTP origin exposed to the browser.
        tts_profile_name: Preferred Voicebox profile name to preselect.
        tts_profiles: Optional Voicebox profile snapshot to embed into the HTML.
        embed_voicebox_profiles: When True, query Voicebox during report generation
            and embed the returned profiles into the voice dropdown.

    Returns:
        A complete HTML document as a string.
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
        section_1_topic_purpose(packet),
        section_2_platform(packet),
        section_3_top_items(packet),
        section_4_platform_engagement(packet),
        section_5_source_validation(packet),
        section_6_evidence(packet),
        section_7_statistics(packet),
        section_8_charts(packet, charts_dir),
        section_9_warnings(packet),
        section_10_synthesis(packet.get("compiled_synthesis")),
        section_11_opportunity(packet.get("opportunity_analysis")),
        section_12_summary(resolve_report_summary(packet)),
    ]
    body_html = _build_body(packet, section_bodies)
    toc_html = _build_toc()
    return _page_shell(
        packet,
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
    packet: ResearchPacket,
    *,
    prepare_voicebox_audio: bool | None = None,
) -> Path:
    """Write an HTML report to data_dir/reports/ and return its path."""
    cfg = load_active_config()
    data_dir = cfg.data_dir
    if not cfg.stage_enabled("report") or not cfg.service_enabled("html_report"):
        raise RuntimeError("HTML report generation is disabled by config")

    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^\w-]", "-", packet["topic"].lower())[:40].strip("-")
    platform = packet.get("platform", "unknown")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = reports_dir / f"{slug}-{platform}-{ts}.html"

    cfg_logs = _technology_logs_enabled()
    api_base = _voicebox_api_base()
    tts_profiles: list[dict[str, str]] = []
    selected_profile = None
    if cfg.technology_enabled("voicebox"):
        with service_log_sync("voicebox_profiles", packet=packet, cfg_logs_enabled=cfg_logs):
            tts_profiles = _fetch_voicebox_profiles(api_base)
        _write_discovered_voicebox_profile_names(tts_profiles)
        selected_profile = _select_voicebox_profile(
            tts_profiles,
            tts_profile_name=_voicebox_default_profile_name(),
        )
    selected_profile_name = selected_profile["name"] if selected_profile is not None else None
    audio_enabled = (
        _audio_report_enabled()
        if prepare_voicebox_audio is None
        else bool(prepare_voicebox_audio)
    )
    prepared_audio_sources: dict[str, str] = {}
    if audio_enabled and cfg.technology_enabled("voicebox"):
        with service_log_sync("voicebox_audio", packet=packet, cfg_logs_enabled=cfg_logs):
            prepared_audio_sources = _prepare_voiceover_audios(
                packet,
                out_path,
                tts_api_base=api_base,
                tts_profiles=tts_profiles,
                tts_profile_name=selected_profile_name,
            )
    prepared_audio_src = prepared_audio_sources.get(selected_profile_name or "", None)
    prepared_audio_profile_name = selected_profile_name if prepared_audio_src else None
    html_content = render_html(
        packet,
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
    """Build the sidebar table-of-contents HTML."""
    links = "".join(f'<a href="#{sid}">{label}</a>' for sid, label in _SECTIONS)
    return f"<h2>Contents</h2>{links}"


def _build_body(packet: ResearchPacket, section_bodies: list[str]) -> str:
    """Build the <main> report body from section bodies."""
    topic_esc = html.escape(packet["topic"])
    platform_esc = html.escape(packet.get("platform", ""))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        f'<h1 class="report-title">{topic_esc}</h1>',
        f'<p class="report-meta">Platform: {platform_esc} &nbsp;·&nbsp; Generated: {timestamp}</p>',
    ]
    for (sid, label), body in zip(_SECTIONS, section_bodies, strict=True):
        parts.append(f'<section id="{sid}"><h2>{label}</h2>{body}</section>')
    return "\n".join(parts)


def _voicebox_api_base() -> str:
    """Return the Voicebox base URL used by the HTML report runtime."""
    return os.environ.get("SRP_VOICEBOX_API_BASE", _default_voicebox_api_base()).rstrip("/")


def _display_path(path: Path) -> str:
    """Return *path* as a user-facing path, preferring ``~/`` under home."""
    resolved = path.resolve()
    home = Path.home().resolve()
    try:
        relative = resolved.relative_to(home)
    except ValueError:
        return str(resolved)
    return f"~/{relative.as_posix()}"


def serve_report_command(report_path: Path) -> str:
    """Return the recommended local command to open *report_path* via HTTP."""
    return f"srp serve-report --report {shlex.quote(_display_path(report_path))}"


def _voicebox_default_profile_name() -> str:
    """Return the configured preferred Voicebox profile name."""
    try:
        value = str(load_active_config().voicebox.get("default_profile_name", "")).strip()
    except Exception:
        value = ""
    return value or "Jarvis"


def _voicebox_profile_names_path() -> Path:
    """Return the discovered Voicebox profile-name cache path."""
    return load_active_config().data_dir / _VOICEBOX_PROFILE_NAMES_FILENAME


def _normalize_voicebox_profile_name(name: str) -> str:
    """Normalize a Voicebox profile name for matching and deduplication."""
    return re.sub(r"\s+", " ", str(name or "").strip()).casefold()


def _dedupe_voicebox_profile_name(raw_name: str, seen_names: set[str]) -> str:
    """Return a readable, unique profile name without leaking profile IDs."""
    base_name = str(raw_name or "").strip() or "Voicebox Profile"
    candidate = base_name
    suffix = 2
    while _normalize_voicebox_profile_name(candidate) in seen_names:
        candidate = f"{base_name} ({suffix})"
        suffix += 1
    seen_names.add(_normalize_voicebox_profile_name(candidate))
    return candidate


def _write_discovered_voicebox_profile_names(tts_profiles: list[dict[str, str]]) -> None:
    """Overwrite the cached Voicebox profile-name list when profiles were found."""
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
    """Return the normalized lookup name for one Voicebox profile."""
    return _normalize_voicebox_profile_name(profile.get("name", ""))


def _fetch_voicebox_profiles(api_base: str) -> list[dict[str, str]]:
    """Fetch Voicebox profiles from *api_base* and normalize them for the UI."""
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
    """Return whether pre-rendered Voicebox audio is enabled."""
    try:
        cfg = load_active_config()
        return cfg.stage_enabled("report") and cfg.service_enabled("audio_report")
    except Exception:
        return True


def _technology_logs_enabled() -> bool:
    """Return whether technology lifecycle logs are enabled."""
    try:
        return bool(load_active_config().debug.get("technology_logs_enabled", False))
    except Exception:
        return False


def _build_tts_voice_options(
    tts_profiles: list[dict[str, str]],
    selected_profile_name: str | None,
) -> str:
    """Build the Voicebox profile <option> markup for the toolbar dropdown."""
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
    """Return the preferred Voicebox profile for the report."""
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
    """Collapse markdown-ish synthesis text into plain narration text."""
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


def build_voiceover_text(packet: ResearchPacket) -> str | None:
    """Return the summary-only narration text used for prepared audio."""
    sections: list[str] = []
    for label, key in (
        ("Compiled synthesis", "compiled_synthesis"),
        ("Opportunity analysis", "opportunity_analysis"),
    ):
        raw = str(packet.get(key, "") or "").strip()
        if not raw:
            continue
        plain = _markdown_to_voiceover_text(raw)
        if plain:
            sections.append(f"{label}. {plain}")
    final_summary = resolve_report_summary(packet) or ""
    final_summary_plain = _markdown_to_voiceover_text(final_summary) if final_summary else ""
    if final_summary_plain:
        sections.append(f"Final summary. {final_summary_plain}")
    if not sections:
        return None
    return " ".join(sections)


def _prepare_voiceover_audio(
    packet: ResearchPacket,
    report_path: Path,
    *,
    tts_api_base: str,
    tts_profile: dict[str, str] | None,
) -> tuple[str | None, str | None]:
    """Pre-render summary audio for *packet* and return (filename, profile_name)."""
    if not tts_profile:
        return None, None
    text = build_voiceover_text(packet)
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
    packet: ResearchPacket,
    report_path: Path,
    *,
    tts_api_base: str,
    tts_profiles: list[dict[str, str]],
    tts_profile_name: str | None,
) -> dict[str, str]:
    """Pre-render summary audio for all known Voicebox profiles concurrently."""
    text = build_voiceover_text(packet)
    if not text or not tts_profiles:
        return {}

    from social_research_probe.technologies.tts.voicebox import write_audio

    prepared: dict[str, str] = {}

    def build_one(profile: dict[str, str]) -> tuple[str, str]:
        audio_base = _prepared_audio_base(report_path, profile["name"])
        audio_path = write_audio(
            text,
            out_base=audio_base,
            api_base=tts_api_base,
            profile_id=profile["id"],
        )
        return profile["name"], audio_path.name

    with ThreadPoolExecutor(max_workers=len(tts_profiles)) as pool:
        futures = {pool.submit(build_one, profile): profile for profile in tts_profiles}
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


def _prepared_audio_base(report_path: Path, profile_name: str) -> Path:
    """Return the output base path for one prepared profile audio file."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", profile_name).strip("-").lower()[:24] or "voice"
    digest = hashlib.sha1(profile_name.encode("utf-8")).hexdigest()[:8]
    name = f"{report_path.stem}.voicebox.{slug}-{digest}"
    return report_path.with_name(name)


def _page_shell(
    packet: ResearchPacket,
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
    """Assemble the complete HTML document from its parts."""
    title = html.escape(f"Research Report: {packet['topic']}")
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
