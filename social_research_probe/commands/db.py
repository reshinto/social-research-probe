"""srp db subcommand: local SQLite database management."""

from __future__ import annotations

import argparse
import sqlite3

from social_research_probe.utils.core.exit_codes import ExitCode

_TABLES = [
    "research_runs",
    "sources",
    "source_snapshots",
    "comments",
    "transcripts",
    "text_surrogates",
    "warnings",
    "artifacts",
]


def _count_tables(conn: sqlite3.Connection) -> dict[str, int]:
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in _TABLES}


def _path(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config

    print(load_active_config().database_path)
    return ExitCode.SUCCESS


def _init(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.schema import (
        ensure_schema,
    )

    db_path = load_active_config().database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = open_connection(db_path)
    try:
        version = ensure_schema(conn)
    finally:
        conn.close()
    print(f"Database ready at {db_path} (schema v{version})")
    return ExitCode.SUCCESS


def _stats(args: argparse.Namespace) -> int:
    from social_research_probe.config import load_active_config
    from social_research_probe.technologies.persistence.sqlite.connection import open_connection
    from social_research_probe.technologies.persistence.sqlite.schema import ensure_schema

    db_path = load_active_config().database_path
    if not db_path.exists():
        print("db not initialized; run 'srp db init'")
        return ExitCode.SUCCESS
    conn = open_connection(db_path)
    try:
        ensure_schema(conn)
        counts = _count_tables(conn)
    finally:
        conn.close()
    for table, count in counts.items():
        print(f"{table}: {count}")
    return ExitCode.SUCCESS


def run(args: argparse.Namespace) -> int:
    from social_research_probe.commands import DbSubcommand

    if not getattr(args, "db_cmd", None):
        parser = getattr(args, "_db_parser", None)
        if parser:
            parser.print_help()
        return ExitCode.SUCCESS
    if args.db_cmd == DbSubcommand.PATH:
        return _path(args)
    if args.db_cmd == DbSubcommand.INIT:
        return _init(args)
    if args.db_cmd == DbSubcommand.STATS:
        return _stats(args)
    return ExitCode.ERROR
