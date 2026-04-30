.PHONY: help setup test test-fast test-evidence record-golden eval-summary-quality

PY ?= ./.venv/bin/python
PYTEST ?= ./.venv/bin/pytest
# Override with JOBS=4 if your machine has fewer cores.
JOBS ?= auto

help:
	@echo "Targets:"
	@echo "  setup          — configure git hooks (run once after clone)"
	@echo "  test           — full suite, sequential (stable; use when debugging)"
	@echo "  test-fast      — full suite, parallel via pytest-xdist (JOBS=$(JOBS))"
	@echo "  test-evidence  — only tests/unit/evidence/ (fast, no coverage gate)"
	@echo "  eval-summary-quality — nightly real-LLM eval (see docs/llm-reliability-harness.md)"
	@echo "  record-golden  — help for scripts/record_golden.py (manual API recorder)"

setup:
	git config core.hooksPath .githooks
	@echo "Git hooks configured (.githooks/)."

test:
	$(PYTEST) -q

test-fast:
	$(PYTEST) -n $(JOBS) --dist=loadfile -q

test-evidence:
	$(PYTEST) tests/unit/evidence -v --no-cov

record-golden:
	$(PY) scripts/record_golden.py --help

eval-summary-quality:
	$(PY) scripts/eval_summary_quality.py
