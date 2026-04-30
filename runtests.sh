#!/bin/sh
set -e

.venv/bin/ruff check social_research_probe/ tests/ --fix && .venv/bin/ruff format social_research_probe/ tests/

.venv/bin/pytest tests/integration tests/unit tests/contract -n auto --dist=loadfile --cov=social_research_probe --cov-fail-under=0

echo "Done running all tests."
