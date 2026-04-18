#!/bin/sh
set -e

if command -v uvx > /dev/null 2>&1; then
    uv tool install "$(dirname "$0")"
elif command -v pipx > /dev/null 2>&1; then
    pipx install "$(dirname "$0")"
else
    echo "error: install uv (https://docs.astral.sh/uv/) or pipx first" >&2
    exit 1
fi

srp install-skill
echo "Done. Open your project in Claude Code — the SocialResearchProbe skill is ready."
