"""Argparse setup: subcommand registration and root parser construction."""

from __future__ import annotations

import argparse

from social_research_probe.commands import Command, ConfigSubcommand, SpecialCommand


def _add_topics_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register update-topics and show-topics subcommands."""
    ut = sub.add_parser(Command.UPDATE_TOPICS)
    group = ut.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    ut.add_argument("--force", action="store_true")
    ut.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    st = sub.add_parser(Command.SHOW_TOPICS)
    st.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_purposes_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register update-purposes and show-purposes subcommands."""
    up = sub.add_parser(Command.UPDATE_PURPOSES)
    group = up.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    up.add_argument("--force", action="store_true")
    up.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sp = sub.add_parser(Command.SHOW_PURPOSES)
    sp.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_suggestions_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register all suggestion-related subcommands."""
    sug_t = sub.add_parser(Command.SUGGEST_TOPICS)
    sug_t.add_argument("--count", type=int, default=5)
    sug_t.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sug_p = sub.add_parser(Command.SUGGEST_PURPOSES)
    sug_p.add_argument("--count", type=int, default=5)
    sug_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    show_pend = sub.add_parser(Command.SHOW_PENDING)
    show_pend.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    ap = sub.add_parser(Command.APPLY_PENDING)
    ap.add_argument("--topics", default="")
    ap.add_argument("--purposes", default="")
    ap.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    dp = sub.add_parser(Command.DISCARD_PENDING)
    dp.add_argument("--topics", default="")
    dp.add_argument("--purposes", default="")
    dp.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    ss = sub.add_parser(Command.STAGE_SUGGESTIONS)
    ss.add_argument("--from-stdin", action="store_true")
    ss.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_research_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register research, corroboration, render, and install-skill subcommands."""
    rs = sub.add_parser(
        Command.RESEARCH,
        help="Simple form: research [platform] TOPIC PURPOSES (purposes comma-separated)",
    )
    rs.add_argument("args", nargs="+", help="[PLATFORM] TOPIC PURPOSE[,PURPOSE...]")
    rs.add_argument(
        "--no-shorts",
        action="store_true",
        help="Exclude YouTube Shorts (<90s) from results",
    )
    rs.add_argument(
        "--no-transcripts",
        action="store_true",
        help="Skip transcript fetching for top-N items (faster, less context)",
    )
    rs.add_argument(
        "--no-html",
        action="store_true",
        help="Skip writing the HTML report to the reports directory",
    )
    cc = sub.add_parser(Command.CORROBORATE_CLAIMS, help="Corroborate claims from a JSON file")
    cc.add_argument("--input", required=True, help="Path to claims JSON file")
    cc.add_argument("--backends", default="llm_search", help="Comma-separated backend names")
    cc.add_argument("--output", default=None, help="Output file path (default: stdout)")
    rend = sub.add_parser(Command.RENDER, help="Render charts and stats for a research packet")
    rend.add_argument("--packet", required=True, help="Path to packet JSON file")
    rend.add_argument("--output-dir", default=None, help="Directory to save charts")
    ins = sub.add_parser(Command.INSTALL_SKILL, help="Copy skill files into ~/.claude/skills/srp")
    ins.add_argument("--target", default=None, help="Destination (default: ~/.claude/skills/srp)")
    sub.add_parser(
        Command.SETUP,
        help="Interactive first-time setup: default config + LLM + API keys",
    )
    rep = sub.add_parser(Command.REPORT, help="Re-render an HTML report from a saved packet file")
    rep.add_argument("--packet", required=True, help="Path to packet JSON file")
    rep.add_argument(
        "--compiled-synthesis",
        default=None,
        dest="compiled_synthesis_path",
        help="File with Compiled Synthesis text",
    )
    rep.add_argument(
        "--opportunity-analysis",
        default=None,
        dest="opportunity_analysis_path",
        help="File with Opportunity Analysis text",
    )
    rep.add_argument(
        "--final-summary",
        default=None,
        dest="final_summary_path",
        help="File with Final Summary text",
    )
    rep.add_argument("--out", default=None, help="Output HTML path (default: stdout)")
    serve = sub.add_parser(
        Command.SERVE_REPORT, help="Serve one HTML report with a local Voicebox proxy"
    )
    serve.add_argument("--report", required=True, help="Path to an existing HTML report")
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve.add_argument(
        "--voicebox-base",
        default=None,
        help="Voicebox API base URL (default: SRP_VOICEBOX_API_BASE or http://127.0.0.1:17493)",
    )


def _add_config_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register the config subcommand with its own sub-actions."""
    cfg = sub.add_parser(Command.CONFIG)
    cfg_sub = cfg.add_subparsers(dest="config_cmd", metavar="ACTION")
    cfg_show = cfg_sub.add_parser(ConfigSubcommand.SHOW)
    cfg_show.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    cfg_path = cfg_sub.add_parser(ConfigSubcommand.PATH)
    cfg_path.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    set_p = cfg_sub.add_parser(ConfigSubcommand.SET)
    set_p.add_argument("key")
    set_p.add_argument("value")
    set_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sec_p = cfg_sub.add_parser(ConfigSubcommand.SET_SECRET)
    sec_p.add_argument("name")
    sec_p.add_argument("--from-stdin", action="store_true")
    sec_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    unset_p = cfg_sub.add_parser(ConfigSubcommand.UNSET_SECRET)
    unset_p.add_argument("name")
    unset_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    check_p = cfg_sub.add_parser(ConfigSubcommand.CHECK_SECRETS)
    check_p.add_argument("--needed-for", default=None)
    check_p.add_argument("--platform", default=None)
    check_p.add_argument("--corroboration", default=None)
    check_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _global_parser() -> argparse.ArgumentParser:
    """Build and return the root argument parser."""
    parser = argparse.ArgumentParser(
        prog="srp", description="Evidence-first social-media research."
    )
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        f"--{SpecialCommand.VERSION}",
        action="store_true",
        help="Print version and resolved package path, then exit.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    _add_topics_subparsers(sub)
    _add_purposes_subparsers(sub)
    _add_suggestions_subparsers(sub)
    _add_research_subparsers(sub)
    _add_config_subparsers(sub)
    return parser
