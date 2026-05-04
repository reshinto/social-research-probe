"""Tests for demo-report CLI integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from social_research_probe.cli.handlers import handlers_factory
from social_research_probe.cli.parsers import global_parser
from social_research_probe.commands import Command


def test_command_enum_has_demo_report():
    assert Command.DEMO_REPORT.value == "demo-report"


def test_handlers_factory_registers_demo_report():
    handlers = handlers_factory()
    assert Command.DEMO_REPORT in handlers


def test_parser_accepts_demo_report():
    parser = global_parser()
    args = parser.parse_args(["demo-report"])
    assert args.command == "demo-report"


def test_handler_dispatches_to_demo_run():
    handlers = handlers_factory()
    handler = handlers[Command.DEMO_REPORT]

    with patch("social_research_probe.commands.demo.run", return_value=0) as mock_run:
        rc = handler(object())
    assert rc == 0
    mock_run.assert_called_once()


@pytest.mark.parametrize(
    "expected_command",
    [
        Command.RESEARCH,
        Command.REPORT,
        Command.CONFIG,
        Command.SERVE_REPORT,
        Command.CORROBORATE_CLAIMS,
    ],
)
def test_existing_commands_still_registered(expected_command):
    assert expected_command in handlers_factory()
