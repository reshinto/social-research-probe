.PHONY: help test test-evidence record-golden

PY ?= ./.venv/bin/python
PYTEST ?= ./.venv/bin/pytest

help:
	@echo "Targets:"
	@echo "  test           — run the full test suite (unit + integration + contract + evidence)"
	@echo "  test-evidence  — run only the evidence test suite under tests/evidence/"
	@echo "  record-golden  — help for scripts/record_golden.py (real API recorder; run manually)"

test:
	$(PYTEST) -q

test-evidence:
	$(PYTEST) tests/evidence -v --no-cov

record-golden:
	$(PY) scripts/record_golden.py --help
