"""Install the srp Claude Code skill and CLI tool.

Called by the ``install-skill`` CLI subcommand. Copies the bundled
``skill/`` directory tree into the user's ``~/.claude/skills/srp``
directory (or a custom target), then permanently installs the ``srp``
CLI via ``uv tool`` or ``pipx`` so it is available on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from social_research_probe.errors import ValidationError

_PACKAGE_REPO = "git+https://github.com/reshinto/social-research-probe"


def run(target: str | None) -> int:
    """Copy the skill tree and install the CLI.

    Args:
        target: Destination path string, or ``None`` to use the default
            ``~/.claude/skills/srp``.

    Returns:
        Exit code — always 0 on success.

    Raises:
        ValidationError: If *target* resolves outside ``~/.claude/``.
    """
    src = Path(__file__).parent.parent / "skill"
    dest = Path(target).resolve() if target else Path.home() / ".claude" / "skills" / "srp"
    _validate_target(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    print(f"Skill installed to {dest}")
    _install_cli()
    return 0


def _validate_target(dest: Path) -> None:
    allowed_root = Path.home() / ".claude"
    if not str(dest).startswith(str(allowed_root)):
        raise ValidationError(f"--target must be inside {allowed_root}")


def _install_cli() -> None:
    if shutil.which("uv"):
        subprocess.run(["uv", "tool", "install", "--reinstall", _PACKAGE_REPO], check=True)
        print("srp CLI installed via uv tool")
    elif shutil.which("pipx"):
        subprocess.run(["pipx", "install", "--force", _PACKAGE_REPO], check=True)
        print("srp CLI installed via pipx")
    else:
        print("warning: neither uv nor pipx found — srp CLI not permanently installed")
        print(f'  run: pipx install "{_PACKAGE_REPO}"')
