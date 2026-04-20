"""Social Research Probe — Evidence-first social-media research CLI + Claude Code skill."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("social-research-probe")
except PackageNotFoundError:
    _version_file = Path(__file__).parent.parent / "VERSION"
    __version__ = _version_file.read_text().strip() if _version_file.exists() else "0.2.0"
