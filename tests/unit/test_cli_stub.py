"""CLI stub: --help works, unknown subcommand exits 2, no subcommand exits 2."""
from __future__ import annotations

import subprocess
import sys


def _run_srp(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "social_research_probe", *args],
        capture_output=True,
        text=True,
    )


def test_help_exits_zero():
    result = _run_srp("--help")
    assert result.returncode == 0
    assert "srp" in result.stdout.lower()
    assert "usage" in result.stdout.lower()


def test_no_subcommand_exits_2():
    result = _run_srp()
    assert result.returncode == 2


def test_unknown_subcommand_exits_2():
    result = _run_srp("bogus-command")
    assert result.returncode == 2
