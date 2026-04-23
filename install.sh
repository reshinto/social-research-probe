#!/bin/sh
set -e

python3.13 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
srp install-skill

echo "Done. Open your project in Claude Code — the SocialResearchProbe skill is ready."
