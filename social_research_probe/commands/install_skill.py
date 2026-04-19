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

from social_research_probe.config import resolve_data_dir
from social_research_probe.errors import ValidationError

_PACKAGE_REPO = "git+https://github.com/reshinto/social-research-probe"

# Ordered list of (secret_name, human_readable_description) pairs shown
# during the interactive setup prompt.
_KEY_PROMPTS: list[tuple[str, str]] = [
    ("youtube_api_key", "YouTube Data API v3 key (required for YouTube search)"),
    ("brave_api_key", "Brave Search API key (corroboration — paid)"),
    ("exa_api_key", "Exa search API key (corroboration — free tier available)"),
    ("tavily_api_key", "Tavily search API key (corroboration — free tier available)"),
]


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
    _prompt_for_secrets(resolve_data_dir(None))
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


def _prompt_for_secrets(data_dir: Path, *, _input: object = input) -> None:
    """Interactively prompt for API keys and save non-blank answers to secrets.toml.

    Iterates over every known key, shows the description and masked current
    value if one already exists, then reads a line from the terminal. A blank
    or whitespace-only response skips that key without modifying anything.
    Any non-blank value is written via write_secret so it persists across runs.

    Exits the loop early on EOFError or KeyboardInterrupt so piped or
    non-interactive installs are never blocked.
    """
    from social_research_probe.commands.config import mask_secret, read_secret, write_secret

    print("\nAPI key setup — press Enter to skip any key:")
    for name, description in _KEY_PROMPTS:
        existing = read_secret(data_dir, name)
        suffix = f"  [current: {mask_secret(existing)}]" if existing else ""
        try:
            value = str(_input(f"  {description}{suffix}:\n  > ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if value:
            write_secret(data_dir, name, value)
            print("    saved.")
