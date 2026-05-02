"""Tests for db CLI parser registration and handler dispatch."""

from __future__ import annotations

from social_research_probe.cli.handlers import handlers_factory
from social_research_probe.cli.parsers import global_parser
from social_research_probe.commands import Command, DbSubcommand


def test_command_enum_has_db():
    assert Command.DB == "db"


def test_db_subcommand_values():
    assert DbSubcommand.INIT == "init"
    assert DbSubcommand.STATS == "stats"
    assert DbSubcommand.PATH == "path"


def test_handlers_factory_registers_db():
    assert Command.DB in handlers_factory()


def test_parser_accepts_db_init():
    args = global_parser().parse_args(["db", "init"])
    assert args.command == "db"
    assert args.db_cmd == "init"


def test_parser_accepts_db_stats():
    args = global_parser().parse_args(["db", "stats"])
    assert args.db_cmd == "stats"


def test_parser_accepts_db_path():
    args = global_parser().parse_args(["db", "path"])
    assert args.db_cmd == "path"


def test_parser_db_no_subcommand_parses():
    args = global_parser().parse_args(["db"])
    assert args.command == "db"
    assert args.db_cmd is None


def test_dispatch_db_handler_calls_db_run():
    from unittest.mock import patch

    h = handlers_factory()
    args = global_parser().parse_args(["db", "path"])
    with patch("social_research_probe.commands.db.run", return_value=0) as mock_run:
        result = h[Command.DB](args)
    mock_run.assert_called_once_with(args)
    assert result == 0
