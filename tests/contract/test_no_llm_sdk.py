"""Hard Invariant #2: no LLM SDK imports anywhere in src/.

Rationale: the skill must never bundle a Python LLM client. Skill mode uses the
host LLM; CLI mode subprocesses external LLM CLIs. Every import of these packages
is a spec violation.
"""

from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_TOP_LEVEL = {"anthropic", "openai", "cohere"}
FORBIDDEN_DOTTED = {"google.generativeai", "google.genai"}

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "social_research_probe"

_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(?P<from_pkg>[\w.]+)\s+import\s+|import\s+(?P<import_pkg>[\w.,\s]+))",
    re.MULTILINE,
)


def _iter_imports(content: str) -> list[str]:
    imports: list[str] = []
    for match in _IMPORT_RE.finditer(content):
        if pkg := match.group("from_pkg"):
            imports.append(pkg)
        elif raw := match.group("import_pkg"):
            for chunk in raw.split(","):
                imports.append(chunk.strip().split(" as ")[0].strip())
    return imports


def test_no_llm_sdk_in_source():
    violations: list[tuple[Path, str]] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        for imp in _iter_imports(py_file.read_text(encoding="utf-8")):
            top = imp.split(".")[0]
            if top in FORBIDDEN_TOP_LEVEL or imp in FORBIDDEN_DOTTED:
                violations.append((py_file, imp))
    assert not violations, "LLM SDK imports are forbidden; found: " + ", ".join(
        f"{p}:{imp}" for p, imp in violations
    )


def test_forbidden_packages_not_in_pyproject():
    pyproject = (SRC_ROOT.parents[1] / "pyproject.toml").read_text()
    for pkg in FORBIDDEN_TOP_LEVEL | {"google-generativeai", "google-genai"}:
        # Use a negative lookahead so "openai-whisper" (local transcription lib,
        # not the OpenAI API SDK) does not trigger the openai prohibition.
        pattern = re.compile(re.escape(pkg) + r"(?!-)", re.IGNORECASE)
        assert not pattern.search(pyproject), f"{pkg} must not appear in pyproject.toml"
