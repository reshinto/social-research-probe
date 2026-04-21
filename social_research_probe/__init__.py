"""Social Research Probe — Evidence-first social-media research CLI + Claude Code skill."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

# Resolution order: VERSION file (dev/editable install) → installed package
# metadata (frozen wheel) → hard-coded fallback. The VERSION file is the
# canonical source for editable installs; reading it first prevents stale
# dist-info metadata after a version bump from causing import-time mismatch.
_version_file = Path(__file__).parent.parent / "VERSION"
if _version_file.exists():
    __version__ = _version_file.read_text().strip()
else:
    try:
        __version__ = version("social-research-probe")
    except PackageNotFoundError:
        __version__ = "0.2.0"
