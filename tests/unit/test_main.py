"""Tests that __main__.py is executable as a module and that __init__.py handles missing metadata."""

import runpy
import sys

import pytest


def test_module_main_calls_cli(monkeypatch):
    """Running python -m social_research_probe exits with an integer code."""
    calls = []
    monkeypatch.setattr("social_research_probe.cli.main", lambda: calls.append(1) or 0)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("social_research_probe", run_name="__main__")
    assert exc.value.code == 0


def test_version_fallback_when_package_not_found(monkeypatch):
    """__init__.py falls back to '0.1.0' when importlib.metadata.version raises."""
    from importlib.metadata import PackageNotFoundError

    monkeypatch.setattr(
        "importlib.metadata.version",
        lambda name: (_ for _ in ()).throw(PackageNotFoundError(name)),
    )
    # Remove the cached module so the except branch re-executes.
    monkeypatch.delitem(sys.modules, "social_research_probe", raising=False)
    import social_research_probe as srp

    assert srp.__version__ == "0.1.0"
