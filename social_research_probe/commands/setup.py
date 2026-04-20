"""Interactive setup wizard for first-time users.

Exposes ``run(data_dir)`` which copies the default config, prompts for an
LLM runner, and prompts for each API key in sequence. Reuses the prompt
helpers already defined in ``install_skill`` so there is a single source
of truth for the key list and runner menu.
"""

from __future__ import annotations

from pathlib import Path

from social_research_probe.commands.install_skill import (
    _copy_config_example,
    _prompt_for_runner,
    _prompt_for_secrets,
)


def run(data_dir: Path) -> int:
    """Run the first-time setup wizard: config scaffold, runner, secrets."""
    print("Welcome to social-research-probe setup.")
    print(
        "This wizard writes a default config and prompts for each API key in turn.\n"
        "Press Enter at any prompt to skip that step — you can re-run `srp setup`\n"
        "or `srp config set-secret <name>` later.\n"
    )
    _copy_config_example(data_dir)
    _prompt_for_runner(data_dir)
    _prompt_for_secrets(data_dir)
    print('\nSetup complete. Try: srp research "AI safety" "latest-news"')
    return 0
