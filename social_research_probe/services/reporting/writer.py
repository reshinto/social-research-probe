"""Report output generation and file writing."""

from __future__ import annotations

from social_research_probe.services.synthesizing.formatter import render_full
from social_research_probe.technologies.report_render.html.raw_html.youtube import (
    serve_report_command,
    write_html_report,
)
from social_research_probe.utils.core.flags import service_flag, stage_flag


def write_final_report(report: dict, *, allow_html: bool) -> str:
    """Write final report and return access path or command.

    Produces both HTML and Markdown. Markdown is fallback when HTML
    generation disabled or fails, ensuring consistent output.
    """
    from social_research_probe.config import load_active_config
    data_dir = load_active_config().data_dir
    html_on = (
        allow_html
        and stage_flag("report", platform="youtube", default=True)
        and service_flag("html", default=True)
        and "multi" not in report
    )
    if html_on:
        try:
            path = write_html_report(
                report,
                prepare_voicebox_audio=service_flag("audio", default=True),
            )
            uri = path.resolve().as_uri()
            report["html_report_path"] = uri
            command = serve_report_command(path)
            report["html_report_command"] = command
            return command
        except Exception:
            pass
    md_path = data_dir / "report.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        body = render_full(report) if "multi" not in report else "# Report\n\n_(no content)_\n"
    except Exception:
        body = "# Report\n\n_(no content — every feature disabled or pipeline empty)_\n"
    md_path.write_text(body, encoding="utf-8")
    return str(md_path.resolve())
