"""Contract: no Python file in src/ or tests/ should use typing.Any."""

from __future__ import annotations

import ast
from pathlib import Path


def _python_files() -> list[Path]:
    roots = [Path("social_research_probe"), Path("tests")]
    return sorted(path for root in roots for path in root.rglob("*.py"))


def test_no_any_in_annotations_or_imports() -> None:
    """Fail when a Python file imports or references ``Any`` in code."""
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                if any(alias.name == "Any" for alias in node.names):
                    offenders.append(f"{path}: imports typing.Any")
            elif isinstance(node, ast.Name) and node.id == "Any":
                offenders.append(f"{path}:{node.lineno}")
    assert offenders == [], "typing.Any is forbidden:\n" + "\n".join(offenders)
