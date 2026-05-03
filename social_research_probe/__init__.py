"""Social Research Probe — Evidence-first social-media research CLI + Claude Code skill."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def get_version() -> str:
    """Return the installed distribution version when available.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            get_version()
        Output:
            "AI safety"
    """
    # In development, the VERSION file might be updated without reinstalling
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.is_file():
        return version_file.read_text().strip()

    try:
        return version("social-research-probe")

    except PackageNotFoundError:
        return "unknown"


__version__ = get_version()
