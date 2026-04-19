"""Tests that __main__.py is executable as a module."""
import runpy

import pytest


def test_module_main_calls_cli(monkeypatch):
    """Running python -m social_research_probe exits with an integer code."""
    calls = []
    monkeypatch.setattr("social_research_probe.cli.main", lambda: calls.append(1) or 0)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("social_research_probe", run_name="__main__")
    assert exc.value.code == 0
