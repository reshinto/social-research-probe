"""Contract: VERSION file, pyproject.toml dynamic version, and __version__ agree."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_version_file_matches_package_version():
    root = Path(__file__).parent.parent.parent
    version_file = (root / "VERSION").read_text().strip()
    import social_research_probe

    assert social_research_probe.__version__ == version_file, (
        f"__version__ ({social_research_probe.__version__!r}) != VERSION file ({version_file!r})"
    )


def test_pyproject_uses_dynamic_version():
    root = Path(__file__).parent.parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert "version" in data["project"].get("dynamic", []), (
        "pyproject.toml [project] must use dynamic = ['version'] driven by VERSION file"
    )


def test_hatch_version_path_points_to_version_file():
    root = Path(__file__).parent.parent.parent
    with open(root / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    hatch_path = data.get("tool", {}).get("hatch", {}).get("version", {}).get("path", "")
    assert hatch_path == "VERSION", (
        f"[tool.hatch.version] path must be 'VERSION', got {hatch_path!r}"
    )
