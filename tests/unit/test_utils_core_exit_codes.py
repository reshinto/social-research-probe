"""Tests for utils.core.exit_codes."""

from social_research_probe.utils.core.exit_codes import ExitCode


def test_success_zero():
    assert ExitCode.SUCCESS == 0


def test_error_two():
    assert ExitCode.ERROR == 2


def test_intenum():
    assert int(ExitCode.SUCCESS) == 0
    assert int(ExitCode.ERROR) == 2
