"""Test that fetch.py is importable without errors."""


def test_fetch_module_imports():
    import social_research_probe.platforms.youtube.fetch  # noqa: F401
