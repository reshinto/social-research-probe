"""Argparse setup: subcommand registration and root parser construction."""

from __future__ import annotations

import argparse


def _add_topics_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register update-topics and show-topics subcommands."""
    ut = sub.add_parser("update-topics")
    group = ut.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    ut.add_argument("--force", action="store_true")
    ut.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    st = sub.add_parser("show-topics")
    st.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_purposes_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register update-purposes and show-purposes subcommands."""
    up = sub.add_parser("update-purposes")
    group = up.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--remove")
    group.add_argument("--rename")
    up.add_argument("--force", action="store_true")
    up.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sp = sub.add_parser("show-purposes")
    sp.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_suggestions_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register all suggestion-related subcommands."""
    sug_t = sub.add_parser("suggest-topics")
    sug_t.add_argument("--count", type=int, default=5)
    sug_t.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sug_p = sub.add_parser("suggest-purposes")
    sug_p.add_argument("--count", type=int, default=5)
    sug_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    show_pend = sub.add_parser("show-pending")
    show_pend.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    ap = sub.add_parser("apply-pending")
    ap.add_argument("--topics", default="")
    ap.add_argument("--purposes", default="")
    ap.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    dp = sub.add_parser("discard-pending")
    dp.add_argument("--topics", default="")
    dp.add_argument("--purposes", default="")
    dp.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    ss = sub.add_parser("stage-suggestions")
    ss.add_argument("--from-stdin", action="store_true")
    ss.add_argument("--output", choices=["text", "json", "markdown"], default="text")


def _add_research_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register research, corroboration, render, and install-skill subcommands."""
    rs = sub.add_parser(
        "research",
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
    cc = sub.add_parser("corroborate-claims", help="Corroborate claims from a JSON file")
    cc.add_argument("--input", required=True, help="Path to claims JSON file")
    cc.add_argument("--backends", default="llm_search", help="Comma-separated backend names")
    cc.add_argument("--output", default=None, help="Output file path (default: stdout)")
    rend = sub.add_parser("render", help="Render charts and stats for a research packet")
    rend.add_argument("--packet", required=True, help="Path to packet JSON file")
    rend.add_argument("--output-dir", default=None, help="Directory to save charts")
    ins = sub.add_parser("install-skill", help="Copy skill files into ~/.claude/skills/srp")
    ins.add_argument("--target", default=None, help="Destination (default: ~/.claude/skills/srp)")
    sub.add_parser("setup", help="Interactive first-time setup: default config + LLM + API keys")
    rep = sub.add_parser("report", help="Re-render an HTML report from a saved packet file")
    rep.add_argument("--packet", required=True, help="Path to packet JSON file")
    rep.add_argument(
        "--synthesis-10",
        default=None,
        dest="synthesis_10",
        help="File with compiled synthesis text",
    )
    rep.add_argument(
        "--synthesis-11",
        default=None,
        dest="synthesis_11",
        help="File with opportunity analysis text",
    )
    rep.add_argument("--out", default=None, help="Output HTML path (default: stdout)")


def _add_config_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register the config subcommand with its own sub-actions."""
    cfg = sub.add_parser("config")
    cfg_sub = cfg.add_subparsers(dest="config_cmd", metavar="ACTION")
    cfg_show = cfg_sub.add_parser("show")
    cfg_show.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    cfg_path = cfg_sub.add_parser("path")
    cfg_path.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    set_p = cfg_sub.add_parser("set")
    set_p.add_argument("key")
    set_p.add_argument("value")
    set_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    sec_p = cfg_sub.add_parser("set-secret")
    sec_p.add_argument("name")
    sec_p.add_argument("--from-stdin", action="store_true")
    sec_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    unset_p = cfg_sub.add_parser("unset-secret")
    unset_p.add_argument("name")
    unset_p.add_argument("--output", choices=["text", "json", "markdown"], default="text")
    check_p = cfg_sub.add_parser("check-secrets")
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
        "--version",
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
