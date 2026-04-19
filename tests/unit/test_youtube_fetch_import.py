"""Test that fetch.py is importable without errors."""


def test_fetch_module_imports():
    import importlib

    importlib.import_module("social_research_probe.platforms.youtube.fetch")
