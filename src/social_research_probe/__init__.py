"""Social Research Probe — Evidence-first social-media research CLI + Claude Code skill."""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("social-research-probe")
except PackageNotFoundError:
    __version__ = "0.1.0"
