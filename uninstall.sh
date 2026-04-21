#!/bin/sh
set -e

source .venv/bin/activate
pip uninstall -y social-research-probe
uv tool uninstall social-research-probe

echo "Done. deactivate and delete .venv to complete uninstallation"
