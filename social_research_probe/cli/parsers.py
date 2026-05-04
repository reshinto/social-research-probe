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

from social_research_probe.commands import (
    ClaimsSubcommand,
    Command,
    CompareSubcommand,
    ConfigSubcommand,
    DbSubcommand,
    NotifySubcommand,
    ScheduleSubcommand,
    WatchSubcommand,
)


class Action(StrEnum):
    """Argparse action names used by this module.

    The enum avoids repeating raw action strings throughout parser setup and keeps action
    values discoverable in one place.

    Examples:
        Input:
            Action
        Output:
            Action
    """

    STORE_TRUE = "store_true"


class Default:
    """Default CLI option values.

    These constants define fallback values for arguments that are optional at the command
    line, such as server host, server port, suggestion count, and default corroboration
    providers.

    Examples:
        Input:
            Default
        Output:
            Default
    """

    PROVIDERS: str = "llm_search"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    SUGGESTION_COUNT: int = 5
    EMPTY: str = ""


class OutputFormat(StrEnum):
    """Supported output formats for commands that render user-facing results.

    Examples:
        Input:
            OutputFormat
        Output:
            OutputFormat
    """

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class Arg(StrEnum):
    """CLI argument names used across parser registration.

    This enum provides a single source of truth for positional and optional argument names.

    It reduces typo risk and makes shared flags easier to update across subcommands.

    Examples:
        Input:
            Arg
        Output:
            Arg
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
    TOPIC = "--topic"
    PURPOSE = "--purpose"
    ENABLED = "--enabled"
    DISABLED = "--disabled"
    INTERVAL = "--interval"
    ALERT_RULE = "--alert-rule"
    WATCH_ID = "--watch-id"
    LIMIT = "--limit"
    CHANNEL = "--channel"
    NOTIFY = "--notify"
    # Global flags
    DATA_DIR = "--data-dir"
    VERBOSE = "--verbose"
    VERSION = "--version"


def _add_output_arg(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``--output`` format argument to a parser.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        parser: Argparse parser receiving shared options or subcommands.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_output_arg(
                parser=argparse.ArgumentParser(prog="srp"),
            )
        Output:
            None
    """
    parser.add_argument(Arg.OUTPUT, choices=list(OutputFormat), default=OutputFormat.TEXT)


def _add_mutation_group(parser: argparse.ArgumentParser) -> None:
    """Add mutually exclusive mutation flags to a parser.

    The mutation group is used by commands that modify stored topics or purposes. Exactly
    one mutation operation is required, while ``--force`` is available as an additional
    safety override.

    Args:
        parser: Argparse parser receiving shared options or subcommands.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_mutation_group(
                parser=argparse.ArgumentParser(prog="srp"),
            )
        Output:
            None
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
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_topics_subparsers(
                sub=subparsers,
            )
        Output:
            None
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
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_purposes_subparsers(
                sub=subparsers,
            )
        Output:
            None
    """
    up = sub.add_parser(Command.UPDATE_PURPOSES)
    _add_mutation_group(up)
    _add_output_arg(up)
    sp = sub.add_parser(Command.SHOW_PURPOSES)
    _add_output_arg(sp)


def _add_suggestions_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register suggestion workflow subcommands.

    Adds commands for generating, staging, showing, applying, and discarding suggested
    topics and purposes.

    Args:
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_suggestions_subparsers(
                sub=subparsers,
            )
        Output:
            None
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
    corroborating claims, rendering charts, generating reports, installing skill files,
    running setup, and serving HTML reports locally.

    Args:
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_research_subparsers(
                sub=subparsers,
            )
        Output:
            None
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

    Adds nested ``config`` actions for showing config, resolving config paths, setting
    regular values, managing secrets, and checking required secrets.

    Args:
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_config_subparsers(
                sub=subparsers,
            )
        Output:
            None
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
    """Register database management subcommands.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_db_subparsers(
                sub=subparsers,
            )
        Output:
            None
    """
    db = sub.add_parser(Command.DB, help="Local SQLite database management")
    db.set_defaults(_db_parser=db)
    db_sub = db.add_subparsers(dest="db_cmd", metavar="ACTION")
    db_sub.add_parser(DbSubcommand.INIT, help="Create or migrate the local database")
    db_sub.add_parser(DbSubcommand.STATS, help="Print row counts for each table")
    db_sub.add_parser(DbSubcommand.PATH, help="Print the resolved database path")


def _add_claims_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register claims query and review subcommands.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _add_claims_subparsers(
                sub=subparsers,
            )
        Output:
            None
    """
    claims = sub.add_parser(Command.CLAIMS, help="Query and review extracted claims")
    claims.set_defaults(_claims_parser=claims)
    claims_sub = claims.add_subparsers(dest="claims_cmd", metavar="ACTION")

    list_p = claims_sub.add_parser(ClaimsSubcommand.LIST, help="List claims with filters")
    list_p.add_argument("--run-id", type=int, default=None)
    list_p.add_argument("--topic", default=None)
    list_p.add_argument("--claim-type", default=None)
    list_p.add_argument("--needs-review", action="store_true")
    list_p.add_argument("--needs-corroboration", action="store_true")
    list_p.add_argument("--corroboration-status", default=None)
    list_p.add_argument("--extraction-method", default=None)
    list_p.add_argument("--limit", type=int, default=100)
    _add_output_arg(list_p)

    show_p = claims_sub.add_parser(ClaimsSubcommand.SHOW, help="Show claim details")
    show_p.add_argument("claim_id", help="Claim ID to display")
    _add_output_arg(show_p)

    stats_p = claims_sub.add_parser(ClaimsSubcommand.STATS, help="Claim statistics")
    _add_output_arg(stats_p)

    review_p = claims_sub.add_parser(ClaimsSubcommand.REVIEW, help="Set review status")
    review_p.add_argument("claim_id", help="Claim ID to review")
    review_p.add_argument("--status", required=True)
    review_p.add_argument("--importance", default=None)
    review_p.add_argument("--notes", default="")
    _add_output_arg(review_p)

    note_p = claims_sub.add_parser(ClaimsSubcommand.NOTE, help="Add a note to a claim")
    note_p.add_argument("claim_id", help="Claim ID")
    note_p.add_argument("text", help="Note text")
    _add_output_arg(note_p)


def _add_compare_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register run comparison subcommands.

    Args:
        sub: Argparse subparser collection where command parsers are registered.

    Returns:
        None.

    Examples:
        Input:
            _add_compare_subparsers(
                sub=subparsers,
            )
        Output:
            None
    """
    cmp = sub.add_parser(Command.COMPARE, help="Compare research runs and detect trends")
    cmp.set_defaults(_compare_parser=cmp)
    cmp_sub = cmp.add_subparsers(dest="compare_cmd", metavar="ACTION")

    run_p = cmp_sub.add_parser(CompareSubcommand.RUN, help="Compare two specific runs")
    run_p.add_argument("run_a", help="Baseline run (PK or run_id)")
    run_p.add_argument("run_b", help="Target run (PK or run_id)")
    run_p.add_argument("--export-dir", default=None, help="Directory for export artifacts")
    _add_output_arg(run_p)

    latest_p = cmp_sub.add_parser(CompareSubcommand.LATEST, help="Compare two most recent runs")
    latest_p.add_argument("--topic", default=None)
    latest_p.add_argument("--platform", default=None)
    latest_p.add_argument("--export-dir", default=None, help="Directory for export artifacts")
    _add_output_arg(latest_p)

    list_p = cmp_sub.add_parser(CompareSubcommand.LIST, help="List available runs")
    list_p.add_argument("--topic", default=None)
    list_p.add_argument("--platform", default=None)
    list_p.add_argument("--limit", type=int, default=20)
    _add_output_arg(list_p)


def _add_watch_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register local watch and alert commands."""
    watch = sub.add_parser(Command.WATCH, help="Manage local topic watches and alerts")
    watch.set_defaults(_watch_parser=watch)
    watch_sub = watch.add_subparsers(dest="watch_cmd", metavar="ACTION")

    add_p = watch_sub.add_parser(WatchSubcommand.ADD, help="Add a local watch")
    add_p.add_argument(Arg.TOPIC, required=True)
    add_p.add_argument(Arg.PLATFORM, default="youtube")
    add_p.add_argument(Arg.PURPOSE, action="append", dest="purposes", default=[])
    add_p.add_argument(Arg.INTERVAL, default=None)
    add_p.add_argument(Arg.ALERT_RULE, action="append", dest="alert_rules", default=[])
    add_p.add_argument(Arg.OUTPUT_DIR, default=None)
    add_p.add_argument(Arg.DISABLED, action=Action.STORE_TRUE)
    _add_output_arg(add_p)

    list_p = watch_sub.add_parser(WatchSubcommand.LIST, help="List local watches")
    list_p.add_argument(Arg.ENABLED, action=Action.STORE_TRUE)
    _add_output_arg(list_p)

    remove_p = watch_sub.add_parser(WatchSubcommand.REMOVE, help="Remove a local watch")
    remove_p.add_argument("watch_id")
    _add_output_arg(remove_p)

    run_p = watch_sub.add_parser(WatchSubcommand.RUN, help="Run one or all local watches")
    run_p.add_argument("watch_id", nargs="?")
    run_p.add_argument("--export-dir", default=None, help="Directory for comparison artifacts")
    run_p.add_argument(Arg.NOTIFY, action=Action.STORE_TRUE)
    run_p.add_argument(Arg.CHANNEL, action="append", dest="channels", default=[])
    _add_output_arg(run_p)

    due_p = watch_sub.add_parser(WatchSubcommand.RUN_DUE, help="Run due enabled watches")
    due_p.add_argument("--export-dir", default=None, help="Directory for comparison artifacts")
    due_p.add_argument(Arg.NOTIFY, action=Action.STORE_TRUE)
    due_p.add_argument(Arg.CHANNEL, action="append", dest="channels", default=[])
    _add_output_arg(due_p)

    alerts_p = watch_sub.add_parser(WatchSubcommand.ALERTS, help="List alert events")
    alerts_p.add_argument(Arg.WATCH_ID, default=None)
    alerts_p.add_argument(Arg.LIMIT, type=int, default=100)
    _add_output_arg(alerts_p)


def _add_notify_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register local notification commands."""
    notify = sub.add_parser(Command.NOTIFY, help="Test local notification channels")
    notify.set_defaults(_notify_parser=notify)
    notify_sub = notify.add_subparsers(dest="notify_cmd", metavar="ACTION")

    test_p = notify_sub.add_parser(NotifySubcommand.TEST, help="Send a test notification")
    test_p.add_argument(Arg.CHANNEL, required=True, choices=["console", "file", "telegram"])
    _add_output_arg(test_p)


def _add_schedule_subparsers(sub: argparse._SubParsersAction) -> None:
    """Register local schedule helper commands."""
    schedule = sub.add_parser(Command.SCHEDULE, help="Print local scheduling helpers")
    schedule.set_defaults(_schedule_parser=schedule)
    schedule_sub = schedule.add_subparsers(dest="schedule_cmd", metavar="ACTION")

    cron_p = schedule_sub.add_parser(ScheduleSubcommand.CRON, help="Print a cron entry")
    cron_p.add_argument(Arg.INTERVAL, choices=["hourly", "daily", "weekly"], default=None)

    launchd_p = schedule_sub.add_parser(ScheduleSubcommand.LAUNCHD, help="Print a launchd plist")
    launchd_p.add_argument(Arg.INTERVAL, choices=["hourly", "daily", "weekly"], default=None)
    launchd_p.add_argument("--output-path", default=None)


def global_parser() -> argparse.ArgumentParser:
    """Build the root ``srp`` argument parser.

    The returned parser includes global flags and all supported subcommands. Command
    dispatch code can use the parsed ``command`` value to route to the correct handler.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            global_parser()
        Output:
            "AI safety"
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
    _add_claims_subparsers(sub)
    _add_compare_subparsers(sub)
    _add_watch_subparsers(sub)
    _add_notify_subparsers(sub)
    _add_schedule_subparsers(sub)
    return parser
