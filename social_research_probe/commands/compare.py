"""srp compare subcommand: run comparison and trend detection."""

from __future__ import annotations

import argparse
import json

from social_research_probe.utils.core.exit_codes import ExitCode


def _open_db() -> tuple[object, int]:
    """Open DB connection, return (conn, exit_code). Exit code non-zero on failure."""
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection

    config = load_active_config()
    db_path = config.database_path
    if not db_path.exists():
        print("Database not found; run 'srp db init' first.")
        return None, ExitCode.ERROR
    conn = open_connection(db_path)
    return conn, ExitCode.SUCCESS


def _resolve_run(conn: object, arg: str) -> dict | None:
    """Resolve a run argument to a row dict (try PK first, then text run_id)."""
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
        get_run,
        get_run_by_text_id,
    )

    try:
        pk = int(arg)
        result = get_run(conn, pk)
        if result is not None:
            return result
    except ValueError:
        pass
    return get_run_by_text_id(conn, arg)


def _build_run_info(row: dict, counts: dict) -> dict:
    """Build a RunInfo object from a row and counts dict."""
    from social_research_probe.utils.comparison.runner import build_run_info

    return build_run_info(row, counts)


def _build_comparison(baseline_row: dict, target_row: dict, conn: object) -> dict:
    """Execute full comparison pipeline between two runs."""
    from social_research_probe.utils.comparison.runner import build_comparison

    return build_comparison(conn, baseline_row, target_row)


def _output_result(result: dict, args: argparse.Namespace) -> int:
    """Format and print comparison result based on --output flag."""
    from pathlib import Path

    from social_research_probe.utils.comparison.export import write_comparison_artifacts
    from social_research_probe.utils.comparison.summary import format_console_summary

    output_fmt = getattr(args, "output", "text")

    if output_fmt == "json":
        print(json.dumps(result, indent=2, default=str))
    else:
        print(format_console_summary(result))

    export_dir = getattr(args, "export_dir", None)
    if export_dir:
        paths = write_comparison_artifacts(result, Path(export_dir))
        print(f"\nExported {len(paths)} artifacts to {export_dir}")

    return ExitCode.SUCCESS


def _compare_runs(args: argparse.Namespace) -> int:
    """Compare two specific runs by ID."""
    conn, code = _open_db()
    if code != ExitCode.SUCCESS:
        return code

    baseline = _resolve_run(conn, args.run_a)
    if baseline is None:
        print(f"Run '{args.run_a}' not found in database.")
        conn.close()
        return ExitCode.ERROR

    target = _resolve_run(conn, args.run_b)
    if target is None:
        print(f"Run '{args.run_b}' not found in database.")
        conn.close()
        return ExitCode.ERROR

    result = _build_comparison(baseline, target, conn)
    conn.close()
    return _output_result(result, args)


def _compare_latest(args: argparse.Namespace) -> int:
    """Compare the two most recent runs."""
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
        get_latest_pair,
    )

    conn, code = _open_db()
    if code != ExitCode.SUCCESS:
        return code

    topic = getattr(args, "topic", None)
    platform = getattr(args, "platform", None)
    pair = get_latest_pair(conn, topic=topic, platform=platform)

    if pair is None:
        from social_research_probe.technologies.persistence.sqlite.comparison_queries import (
            list_runs,
        )

        count = len(list_runs(conn, topic=topic, platform=platform))
        print(f"Need at least 2 runs to compare. Only {count} found.")
        conn.close()
        return ExitCode.ERROR

    baseline, target = pair
    result = _build_comparison(baseline, target, conn)
    conn.close()
    return _output_result(result, args)


def _list_runs(args: argparse.Namespace) -> int:
    """List available runs."""
    from social_research_probe.technologies.persistence.sqlite.comparison_queries import list_runs

    conn, code = _open_db()
    if code != ExitCode.SUCCESS:
        return code

    topic = getattr(args, "topic", None)
    platform = getattr(args, "platform", None)
    limit = getattr(args, "limit", 20)
    runs = list_runs(conn, topic=topic, platform=platform, limit=limit)
    conn.close()

    output_fmt = getattr(args, "output", "text")
    if output_fmt == "json":
        print(json.dumps(runs, indent=2, default=str))
    else:
        if not runs:
            print("No runs found.")
        else:
            for r in runs:
                print(f"  {r['id']:>4}  {r['run_id']:<20}  {r['topic']:<20}  {r['started_at']}")

    return ExitCode.SUCCESS


def run(args: argparse.Namespace) -> int:
    """Dispatch compare subcommands."""
    from social_research_probe.commands import CompareSubcommand

    if not getattr(args, "compare_cmd", None):
        parser = getattr(args, "_compare_parser", None)
        if parser:
            parser.print_help()
        return ExitCode.SUCCESS
    if args.compare_cmd == CompareSubcommand.RUN:
        return _compare_runs(args)
    if args.compare_cmd == CompareSubcommand.LATEST:
        return _compare_latest(args)
    if args.compare_cmd == CompareSubcommand.LIST:
        return _list_runs(args)
    return ExitCode.ERROR
