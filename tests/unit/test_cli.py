"""Tests for cli package: parsers, handlers, main entry."""

from __future__ import annotations

import argparse
from unittest.mock import patch

from social_research_probe.cli import (
    EXIT_INVALID_USAGE,
    EXIT_SUCCESS,
    _dispatch,
    _handle_version,
    main,
)
from social_research_probe.cli.handlers import handlers_factory
from social_research_probe.cli.parsers import (
    Action,
    Arg,
    Default,
    OutputFormat,
    global_parser,
)
from social_research_probe.commands import Command


def test_action_enum():
    assert Action.STORE_TRUE == "store_true"


def test_default_constants():
    assert Default.PROVIDERS == "llm_search"
    assert Default.HOST == "127.0.0.1"
    assert Default.PORT == 8000
    assert Default.SUGGESTION_COUNT == 5


def test_output_format_values():
    assert set(OutputFormat) == {OutputFormat.TEXT, OutputFormat.JSON, OutputFormat.MARKDOWN}


def test_arg_enum_keys():
    assert Arg.OUTPUT == "--output"
    assert Arg.ADD == "--add"


def test_global_parser_known_commands():
    parser = global_parser()
    args = parser.parse_args(["show-topics"])
    assert args.command == "show-topics"
    assert args.output == OutputFormat.TEXT


def test_global_parser_data_dir():
    parser = global_parser()
    args = parser.parse_args(["--data-dir", "/tmp/srp", "show-topics"])
    assert args.data_dir == "/tmp/srp"


def test_global_parser_version():
    parser = global_parser()
    args = parser.parse_args(["--version"])
    assert args.version is True


class TestHandleVersion:
    def test_version_flag_true_prints(self, capsys):
        ns = argparse.Namespace(version=True)
        with patch("social_research_probe.get_version", return_value="0.0.0"):
            assert _handle_version(ns) is True

    def test_version_flag_false(self):
        ns = argparse.Namespace(version=False)
        assert _handle_version(ns) is False


class TestHandlersFactory:
    def test_includes_known_commands(self):
        h = handlers_factory()
        assert Command.UPDATE_TOPICS in h
        assert Command.SHOW_TOPICS in h
        assert Command.RESEARCH in h
        assert Command.CONFIG in h


class TestDispatch:
    def test_unknown_command_returns_invalid(self):
        ns = argparse.Namespace(command="nonexistent", data_dir=None)
        with patch("social_research_probe.cli.handlers_factory", return_value={}):
            assert _dispatch(ns) == EXIT_INVALID_USAGE

    def test_dispatches_to_handler(self):
        ns = argparse.Namespace(command="x", data_dir=None)
        called = {}

        def fake_handler(args):
            called["yes"] = True
            return 0

        with patch("social_research_probe.cli.handlers_factory", return_value={"x": fake_handler}):
            assert _dispatch(ns) == 0
        assert called == {"yes": True}


class TestMain:
    def test_no_command_prints_help_and_returns_2(self, capsys):
        rc = main([])
        assert rc == EXIT_INVALID_USAGE

    def test_version(self, capsys):
        rc = main(["--version"])
        assert rc == EXIT_SUCCESS
        assert "srp" in capsys.readouterr().out

    def test_srp_error_caught(self, capsys, monkeypatch):
        from social_research_probe.utils.core.errors import ValidationError

        def boom(args):
            raise ValidationError("nope")

        monkeypatch.setattr(
            "social_research_probe.cli.handlers_factory", lambda: {"show-topics": boom}
        )
        rc = main(["show-topics"])
        assert rc == ValidationError.exit_code
        assert "error: nope" in capsys.readouterr().err
