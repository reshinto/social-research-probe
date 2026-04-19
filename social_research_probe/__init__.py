"""Social Research Probe — Evidence-first social-media research CLI + Claude Code skill."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("social-research-probe")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.1.0"  # pragma: no cover
