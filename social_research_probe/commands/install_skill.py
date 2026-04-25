"""Install the srp Claude Code skill and CLI tool.

Called by the ``install-skill`` CLI subcommand. Copies the bundled
``skill/`` directory tree into the user's ``~/.claude/skills/srp``
directory (or a custom target), then permanently installs the ``srp``
CLI via ``uv tool`` or ``pipx`` so it is available on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from enum import StrEnum
from pathlib import Path

from social_research_probe.cli.parsers import Arg
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.exit_codes import ExitCode


class PackageManagerFlag(StrEnum):
    FORCE = "--force"
    REINSTALL = "--reinstall"

_PACKAGE_REPO = "git+https://github.com/reshinto/social-research-probe"
_BUNDLED_CONFIG = Path(__file__).resolve().parents[2] / "config.toml.example"

# (secret_name, description, signup_url) — url shown so user can register before entering key.
_KEY_PROMPTS: list[tuple[str, str, str]] = [
    (
        "youtube_api_key",
        "YouTube Data API v3 key (required for YouTube search)",
        "https://console.cloud.google.com/apis/library/youtube.googleapis.com",
    ),
    (
        "brave_api_key",
        "Brave Search API key (corroboration — paid, no free tier)",
        "https://brave.com/search/api/",
    ),
    (
        "exa_api_key",
        "Exa search API key (corroboration — free tier available)",
        "https://dashboard.exa.ai/",
    ),
    (
        "tavily_api_key",
        "Tavily search API key (corroboration — free tier: 1000 credits/month)",
        "https://app.tavily.com/",
    ),
]


# (runner_name, description, signup_url) — url shown so user can sign up before choosing.
_RUNNER_CHOICES: list[tuple[str, str, str]] = [
    (
        "claude",
        "Claude CLI (claude) — requires Anthropic account",
        "https://claude.ai/download",
    ),
    (
        "gemini",
        "Gemini CLI (gemini) — requires Google account",
        "https://github.com/google-gemini/gemini-cli",
    ),
    (
        "codex",
        "Codex CLI (codex) — requires OpenAI account",
        "https://github.com/openai/codex",
    ),
    ("local", "Local model via SRP_LOCAL_LLM_BIN env var", ""),
    ("none", "No LLM — skip all AI features", ""),
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
    _copy_config_example()
    _prompt_for_secrets()
    _ensure_voicebox_secrets()
    _prompt_for_runner()
    return ExitCode.SUCCESS


def _validate_target(dest: Path) -> None:
    allowed_root = Path.home() / ".claude"
    if not str(dest).startswith(str(allowed_root)):
        raise ValidationError(f"{Arg.TARGET} must be inside {allowed_root}")


def _install_cli() -> None:
    if shutil.which("uv"):
        subprocess.run(
            ["uv", "tool", "install", PackageManagerFlag.FORCE, PackageManagerFlag.REINSTALL, _PACKAGE_REPO], check=True
        )
        print("srp CLI installed via uv tool")
    elif shutil.which("pipx"):
        subprocess.run(["pipx", "install", PackageManagerFlag.FORCE, _PACKAGE_REPO], check=True)
        print("srp CLI installed via pipx")
    else:
        print("warning: neither uv nor pipx found — srp CLI not permanently installed")
        print(f'  run: pipx install "{_PACKAGE_REPO}"')


def _copy_config_example() -> None:
    """Seed data_dir/config.toml from the bundled example, or merge missing keys.

    Fresh install: copy the example verbatim.
    Reinstall: additively merge any keys the bundled example has that the
    existing config lacks. Existing user values are never overwritten.
    """
    from social_research_probe.commands.config import CONFIG_FILENAME
    from social_research_probe.config import load_active_config

    data_dir = load_active_config().data_dir
    dest = data_dir / CONFIG_FILENAME
    if not dest.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_BUNDLED_CONFIG, dest)
        print(f"Default config written to {dest}")
        return
    _merge_missing_config_keys(dest)


def _load_and_merge_configs(dest: Path) -> tuple[dict, list[str]]:
    """Load existing and bundled configs, merge missing keys, return merged and list of added keys."""
    with dest.open("rb") as f:
        existing = tomllib.load(f)
    with _BUNDLED_CONFIG.open("rb") as f:
        bundled = tomllib.load(f)

    added: list[str] = []
    _deep_merge_missing(existing, bundled, (), added)
    return existing, added


def _write_merged_config(dest: Path, config: dict) -> None:
    """Write merged config to file in TOML format."""
    from social_research_probe.commands.config import _emit_table, _order_like_template
    from social_research_probe.config import DEFAULT_CONFIG

    ordered = _order_like_template(config, DEFAULT_CONFIG)
    lines: list[str] = []
    for sec, entries in ordered.items():
        _emit_table(sec, entries, lines)
    dest.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _merge_missing_config_keys(dest: Path) -> None:
    """Add keys/sections from the bundled example that are missing in *dest*."""
    config, added = _load_and_merge_configs(dest)
    if not added:
        return
    _write_merged_config(dest, config)
    print(f"Added {len(added)} new config key(s) to {dest}:")
    for key in added:
        print(f"  + {key}")


def _deep_merge_missing(
    target: dict, source: dict, path: tuple[str, ...], added: list[str]
) -> None:
    """Copy keys from *source* into *target* when absent, recursing into tables."""
    for key, value in source.items():
        dotted = ".".join((*path, key))
        if key not in target:
            target[key] = value
            added.append(dotted)
            continue
        if isinstance(value, dict) and isinstance(target[key], dict):
            _deep_merge_missing(target[key], value, (*path, key), added)


def _get_runner_choice(*, _input: object = input) -> str | None:
    """Prompt for runner choice, validate input, return chosen name or None."""
    print("\nDefault LLM runner — choose which AI backend srp should use:")
    for i, (name, description, url) in enumerate(_RUNNER_CHOICES, start=1):
        print(f"  {i}. {name:8}  {description}")
        if url:
            print(f"           Register: {url}")
    try:
        raw = str(_input("  Enter number (or press Enter to skip): ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw:
        return None
    try:
        index = int(raw) - 1
        if index < 0 or index >= len(_RUNNER_CHOICES):
            raise ValueError
    except ValueError:
        print(f"  invalid choice '{raw}' — skipping runner configuration")
        return None
    return _RUNNER_CHOICES[index][0]


def _write_runner_config(runner: str) -> None:
    """Write runner choice and enable corresponding technology gate."""
    from social_research_probe.commands.config import write_config_value

    write_config_value("llm.runner", runner)
    print(f"  runner set to '{runner}'.")
    if runner != "none":
        write_config_value(f"technologies.{runner}", "true")
        print(f"  technologies.{runner} set to true.")


def _prompt_for_runner(*, _input: object = input) -> None:
    """Prompt the user to choose a default LLM runner and persist it to config.toml."""
    chosen = _get_runner_choice(_input=_input)
    if chosen:
        _write_runner_config(chosen)


def _prompt_for_single_secret(name: str, description: str, url: str, *, _input: object = input) -> tuple[str | None, bool]:
    """Prompt user for a single API key. Return (value, should_continue).

    Returns:
        (value, True) if user entered value
        (None, True) if user skipped (blank)
        (None, False) if EOFError/KeyboardInterrupt occurred
    """
    from social_research_probe.commands.config import mask_secret, read_secret

    existing = read_secret(name)
    suffix = f"  [current: {mask_secret(existing)}]" if existing else ""
    if url:
        print(f"  Register: {url}")
    try:
        value = str(_input(f"  {description}{suffix}:\n  > ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None, False
    return value if value else None, True


def _prompt_for_secrets(*, _input: object = input) -> None:
    """Interactively prompt for API keys and save non-blank answers to secrets.toml."""
    from social_research_probe.commands.config import write_secret

    print("\nAPI key setup — press Enter to skip any key:")
    for name, description, url in _KEY_PROMPTS:
        value, should_continue = _prompt_for_single_secret(name, description, url, _input=_input)
        if value:
            write_secret(name, value)
            print("    saved.")
        if not should_continue:
            break


def _get_voicebox_default_url() -> str:
    """Load Voicebox API base URL from config."""
    from social_research_probe.config import load_active_config
    return load_active_config().voicebox["api_base"]


def _ensure_voicebox_secrets() -> None:
    """Auto-write default tts_voicebox_server_url secret if missing."""
    from social_research_probe.commands.config import read_secret, write_secret

    if not read_secret("tts_voicebox_server_url"):
        default_url = _get_voicebox_default_url()
        write_secret("tts_voicebox_server_url", default_url)
        print(f"  tts_voicebox_server_url defaulted to {default_url}")
