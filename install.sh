#!/bin/sh
set -e

if [ "$(git config --get core.hooksPath)" != ".githooks" ]; then
  git config core.hooksPath .githooks
  echo "Git hooks configured (.githooks/)."
fi

python3.13 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
srp install-skill

echo "Done. Open your project in Claude Code — the SocialResearchProbe skill is ready."
