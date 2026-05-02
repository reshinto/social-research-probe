"""Command-line parser construction for the Social Research Probe CLI.

This module centralizes argparse setup for the ``srp`` command-line interface.
It defines shared argument constants, default values, output formats, and helper
functions that register related command groups on the root parser.

Keeping parser construction in one module makes the CLI easier to audit,
extend, and test. Each helper owns one command area, such as topics, purposes,
research, suggestions, or configuration.
"""

from __future__ import annotations

import argparse
from enum import StrEnum

from social_research_probe.commands import Command, ConfigSubcommand, DbSubcommand


class Action(StrEnum):
    """Argparse action names used by this module.

    The enum avoids repeating raw action strings throughout parser setup and
    keeps action values discoverable in one place.
    """

    STORE_TRUE = "store_true"


class Default:
    """Default CLI option values.

    These constants define fallback values for arguments that are optional at
    the command line, such as server host, server port, suggestion count, and
    default corroboration providers.
    """

    PROVIDERS: str = "llm_search"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    SUGGESTION_COUNT: int = 5
    EMPTY: str = ""


class OutputFormat(StrEnum):
    """Supported output formats for commands that render user-facing results."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class Arg(StrEnum):
    """CLI argument names used across parser registration.

    This enum provides a single source of truth for positional and optional
    argument names. It reduces typo risk and makes shared flags easier to
    update across subcommands.
    """

    # Mutation flags
    ADD = "--add"
    REMOVE = "--remove"
    RENAME = "--rename"
    FORCE = "--force"
    # Common output
    OUTPUT = "--output"
    # Suggestion flags
    COUNT = "--count"
    TOPICS = "--topics"
    PURPOSES = "--purposes"
    FROM_STDIN = "--from-stdin"
    # Research flags
    ARGS = "args"
    NO_SHORTS = "--no-shorts"
    NO_TRANSCRIPTS = "--no-transcripts"
    NO_HTML = "--no-html"
    # Corroborate flags
    INPUT = "--input"
    PROVIDERS = "--providers"
    # Render flags
    PACKET = "--packet"
    OUTPUT_DIR = "--output-dir"
    # Install-skill flags
    TARGET = "--target"
    # Report flags
    COMPILED_SYNTHESIS = "--compiled-synthesis"
    OPPORTUNITY_ANALYSIS = "--opportunity-analysis"
    FINAL_SUMMARY = "--final-summary"
    OUT = "--out"
    # Serve-report flags
    REPORT = "--report"
    HOST = "--host"
    PORT = "--port"
    VOICEBOX_BASE = "--voicebox-base"
    # Config flags
    KEY = "key"
    VALUE = "value"
    NAME = "name"
    NEEDED_FOR = "--needed-for"
    PLATFORM = "--platform"
    CORROBORATION = "--corroboration"
    # Global flags
    DATA_DIR = "--data-dir"
    VERBOSE = "--verbose"
    VERSION = "--version"


def _add_output_arg(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--output`` format argument to a parser.

    Args:
        parser: Parser or subparser that should accept an output format.
    """
    parser.add_argument(Arg.OUTPUT, choices=list(OutputFormat), default=OutputFormat.TEXT)


def _add_mutation_group(parser: argparse.ArgumentParser) -> None:
    """Add mutually exclusive mutation flags to a parser.

    The mutation group is used by commands that modify stored topics or
    purposes. Exactly one mutation operation is required, while ``--force`` is
    available as an additional safety override.

    Args:
        parser: Parser that should receive mutation-related arguments.
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(Arg.ADD, nargs="+")
    group.add_argument(Arg.REMOVE, nargs="+")
    group.add_argument(Arg.RENAME, nargs=2)
    parser.add_argument(Arg.FORCE, action=Action.STORE_TRUE)


def _add_topics_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register topic-management subcommands.

    Adds commands for updating and displaying configured research topics.

    Args:
        sub: Root subparser collection that receives topic commands.
    """
    ut = sub.add_parser(Command.UPDATE_TOPICS)
    _add_mutation_group(ut)
    _add_output_arg(ut)
    st = sub.add_parser(Command.SHOW_TOPICS)
    _add_output_arg(st)


def _add_purposes_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register purpose-management subcommands.

    Adds commands for updating and displaying configured research purposes.

    Args:
        sub: Root subparser collection that receives purpose commands.

    """
    up = sub.add_parser(Command.UPDATE_PURPOSES)
    _add_mutation_group(up)
    _add_output_arg(up)
    sp = sub.add_parser(Command.SHOW_PURPOSES)
    _add_output_arg(sp)


def _add_suggestions_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register suggestion workflow subcommands.

    Adds commands for generating, staging, showing, applying, and discarding
    suggested topics and purposes.

    Args:
        sub: Root subparser collection that receives suggestion commands.
    """
    sug_t = sub.add_parser(Command.SUGGEST_TOPICS)
    sug_t.add_argument(Arg.COUNT, type=int, default=Default.SUGGESTION_COUNT)
    _add_output_arg(sug_t)
    sug_p = sub.add_parser(Command.SUGGEST_PURPOSES)
    sug_p.add_argument(Arg.COUNT, type=int, default=Default.SUGGESTION_COUNT)
    _add_output_arg(sug_p)
    show_pend = sub.add_parser(Command.SHOW_PENDING)
    _add_output_arg(show_pend)
    ap = sub.add_parser(Command.APPLY_PENDING)
    ap.add_argument(Arg.TOPICS, default=Default.EMPTY)
    ap.add_argument(Arg.PURPOSES, default=Default.EMPTY)
    _add_output_arg(ap)
    dp = sub.add_parser(Command.DISCARD_PENDING)
    dp.add_argument(Arg.TOPICS, default=Default.EMPTY)
    dp.add_argument(Arg.PURPOSES, default=Default.EMPTY)
    _add_output_arg(dp)
    ss = sub.add_parser(Command.STAGE_SUGGESTIONS)
    ss.add_argument(Arg.FROM_STDIN, action=Action.STORE_TRUE)
    _add_output_arg(ss)


def _add_research_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register research, reporting, rendering, and local serving commands.

    These subcommands cover the main research packet workflow: running research,
    corroborating claims, rendering charts, generating reports, installing skill
    files, running setup, and serving HTML reports locally.

    Args:
        sub: Root subparser collection that receives research-related commands.
    """
    rs = sub.add_parser(
        Command.RESEARCH,
        help="Simple form: research [platform] TOPIC PURPOSES (purposes comma-separated)",
    )
    rs.add_argument(Arg.ARGS, nargs="+", help="[PLATFORM] TOPIC PURPOSE[,PURPOSE...]")
    rs.add_argument(
        Arg.NO_SHORTS,
        action=Action.STORE_TRUE,
        help="Exclude YouTube Shorts (<90s) from results",
    )
    rs.add_argument(
        Arg.NO_TRANSCRIPTS,
        action=Action.STORE_TRUE,
        help="Skip transcript fetching for top-N items (faster, less context)",
    )
    rs.add_argument(
        Arg.NO_HTML,
        action=Action.STORE_TRUE,
        help="Skip writing the HTML report to the reports directory",
    )
    cc = sub.add_parser(Command.CORROBORATE_CLAIMS, help="Corroborate claims from a JSON file")
    cc.add_argument(Arg.INPUT, required=True, help="Path to claims JSON file")
    cc.add_argument(Arg.PROVIDERS, default=Default.PROVIDERS, help="Comma-separated provider names")
    cc.add_argument(Arg.OUTPUT, default=None, help="Output file path (default: stdout)")
    rend = sub.add_parser(Command.RENDER, help="Render charts and stats for a research packet")
    rend.add_argument(Arg.PACKET, required=True, help="Path to packet JSON file")
    rend.add_argument(Arg.OUTPUT_DIR, default=None, help="Directory to save charts")
    ins = sub.add_parser(Command.INSTALL_SKILL, help="Copy skill files into ~/.claude/skills/srp")
    ins.add_argument(Arg.TARGET, default=None, help="Destination (default: ~/.claude/skills/srp)")
    sub.add_parser(
        Command.SETUP,
        help="Interactive first-time setup: default config + LLM + API keys",
    )
    rep = sub.add_parser(Command.REPORT, help="Re-render an HTML report from a saved packet file")
    rep.add_argument(Arg.PACKET, required=True, help="Path to packet JSON file")
    rep.add_argument(
        Arg.COMPILED_SYNTHESIS,
        default=None,
        dest="compiled_synthesis_path",
        help="File with Compiled Synthesis text",
    )
    rep.add_argument(
        Arg.OPPORTUNITY_ANALYSIS,
        default=None,
        dest="opportunity_analysis_path",
        help="File with Opportunity Analysis text",
    )
    rep.add_argument(
        Arg.FINAL_SUMMARY,
        default=None,
        dest="final_summary_path",
        help="File with Final Summary text",
    )
    rep.add_argument(Arg.OUT, default=None, help="Output HTML path (default: stdout)")
    serve = sub.add_parser(
        Command.SERVE_REPORT, help="Serve one HTML report with a local Voicebox proxy"
    )
    serve.add_argument(Arg.REPORT, required=True, help="Path to an existing HTML report")
    serve.add_argument(Arg.HOST, default=Default.HOST, help="Bind host (default: 127.0.0.1)")
    serve.add_argument(Arg.PORT, type=int, default=Default.PORT, help="Bind port (default: 8000)")
    serve.add_argument(
        Arg.VOICEBOX_BASE,
        default=None,
        help="Voicebox API base URL (default: SRP_VOICEBOX_API_BASE env var or config file)",
    )
    sub.add_parser(
        Command.DEMO_REPORT,
        help="Generate a synthetic offline demo report and export package.",
    )


def _add_config_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register configuration and secret-management subcommands.

    Adds nested ``config`` actions for showing config, resolving config paths,
    setting regular values, managing secrets, and checking required secrets.

    Args:
        sub: Root subparser collection that receives the ``config`` command.
    """
    cfg = sub.add_parser(Command.CONFIG)
    cfg_sub = cfg.add_subparsers(dest="config_cmd", metavar="ACTION")
    cfg_show = cfg_sub.add_parser(ConfigSubcommand.SHOW)
    _add_output_arg(cfg_show)
    cfg_path = cfg_sub.add_parser(ConfigSubcommand.PATH)
    _add_output_arg(cfg_path)
    set_p = cfg_sub.add_parser(ConfigSubcommand.SET)
    set_p.add_argument(Arg.KEY)
    set_p.add_argument(Arg.VALUE)
    _add_output_arg(set_p)
    sec_p = cfg_sub.add_parser(ConfigSubcommand.SET_SECRET)
    sec_p.add_argument(Arg.NAME)
    sec_p.add_argument(Arg.FROM_STDIN, action=Action.STORE_TRUE)
    _add_output_arg(sec_p)
    unset_p = cfg_sub.add_parser(ConfigSubcommand.UNSET_SECRET)
    unset_p.add_argument(Arg.NAME)
    _add_output_arg(unset_p)
    check_p = cfg_sub.add_parser(ConfigSubcommand.CHECK_SECRETS)
    check_p.add_argument(Arg.NEEDED_FOR, default=None)
    check_p.add_argument(Arg.PLATFORM, default=None)
    check_p.add_argument(Arg.CORROBORATION, default=None)
    _add_output_arg(check_p)


def _add_db_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register database management subcommands."""
    db = sub.add_parser(Command.DB, help="Local SQLite database management")
    db.set_defaults(_db_parser=db)
    db_sub = db.add_subparsers(dest="db_cmd", metavar="ACTION")
    db_sub.add_parser(DbSubcommand.INIT, help="Create or migrate the local database")
    db_sub.add_parser(DbSubcommand.STATS, help="Print row counts for each table")
    db_sub.add_parser(DbSubcommand.PATH, help="Print the resolved database path")


def global_parser() -> argparse.ArgumentParser:
    """Build the root ``srp`` argument parser.

    The returned parser includes global flags and all supported subcommands.
    Command dispatch code can use the parsed ``command`` value to route to the
    correct handler.

    Returns:
        Fully configured argparse parser for the ``srp`` CLI.
    """
    parser = argparse.ArgumentParser(
        prog="srp", description="Evidence-first social-media research."
    )
    parser.add_argument(Arg.DATA_DIR, default=None)
    parser.add_argument(Arg.VERBOSE, action=Action.STORE_TRUE)
    parser.add_argument(
        Arg.VERSION,
        action=Action.STORE_TRUE,
        help="Print version and resolved package path, then exit.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    _add_topics_subparsers(sub)
    _add_purposes_subparsers(sub)
    _add_suggestions_subparsers(sub)
    _add_research_subparsers(sub)
    _add_config_subparsers(sub)
    _add_db_subparsers(sub)
    return parser
