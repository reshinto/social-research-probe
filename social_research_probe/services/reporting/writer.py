"""Report output generation and file writing."""

from __future__ import annotations

from pathlib import Path

from social_research_probe.services.synthesizing.formatter import render_full
from social_research_probe.technologies.report_render.html.raw_html.youtube import (
    serve_report_command,
    write_html_report,
)
from social_research_probe.utils.core.flags import service_flag, stage_flag


def write_final_report(
    packet: dict,
    data_dir: Path,
    cfg: object,
    *,
    allow_html: bool,
) -> str:
    """Write final report and return access path or command.

    Produces both HTML and Markdown. Markdown is fallback when HTML
    generation disabled or fails, ensuring consistent output.
    """
    html_on = (
        allow_html
        and stage_flag(cfg, "report", default=True)
        and service_flag(cfg, "html_report", default=True)
        and "multi" not in packet
    )
    if html_on:
        try:
            path = write_html_report(
                packet,
                data_dir,
                prepare_voicebox_audio=service_flag(cfg, "audio_report", default=True),
            )
            uri = path.resolve().as_uri()
            packet["html_report_path"] = uri
            command = serve_report_command(path)
            packet["html_report_command"] = command
            return command
        except Exception:
            pass
    md_path = data_dir / "report.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        body = render_full(packet) if "multi" not in packet else "# Report\n\n_(no content)_\n"
    except Exception:
        body = "# Report\n\n_(no content — every feature disabled or pipeline empty)_\n"
    md_path.write_text(body, encoding="utf-8")
    return str(md_path.resolve())
