"""Social Research Probe — Evidence-first social-media research CLI + Claude Code skill."""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed distribution version when available."""
    try:
        return version("social-research-probe")

    except PackageNotFoundError:
        return "unknown"


__version__ = get_version()
