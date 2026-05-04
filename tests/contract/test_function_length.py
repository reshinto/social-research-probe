"""Contract: no function or method in production code may exceed 50 lines.

Engineering Rules: keep most functions 10-30 lines; avoid exceeding 50 unless justified.
Justified exceptions must be added to _WHITELIST with a comment explaining why.
"""

from __future__ import annotations

import ast
from pathlib import Path

_LIMIT = 50

_WHITELIST: frozenset[str] = frozenset(
    {
        # argparse registration: flat API forces verbose option declarations
        "social_research_probe/cli/parsers.py::_add_research_subparsers",
        # builds one ScoredItem TypedDict with 18 fields — inherently verbose assembly
        "social_research_probe/utils/demo/items.py::_build_item",
        # single-purpose arg parser; 20-line docstring with examples inflates count
        "social_research_probe/commands/research.py::_parse_research_input",
        # infrastructure caching layer: cache miss/hit + debug logging + async dispatch
        "social_research_probe/technologies/__init__.py::BaseTechnology._cached_execute",
        # single SQL INSERT with 12 columns; column verbosity is inherent to the schema
        "social_research_probe/technologies/persistence/sqlite/repository.py::insert_snapshot",
        # single SQL INSERT with 24 columns; column verbosity is inherent to the claims schema
        "social_research_probe/technologies/persistence/sqlite/repository.py::insert_claims",
        # single-purpose markdown→HTML conversion; regex patterns are inherently verbose
        "social_research_probe/technologies/report_render/html/raw_html/markdown_to_html.py::md_to_html",
        # assembles one HTML report from 12 pre-built section strings
        "social_research_probe/technologies/report_render/html/raw_html/youtube.py::render_html",
        # writes one HTML report to disk with audio preparation + path resolution
        "social_research_probe/technologies/report_render/html/raw_html/youtube.py::write_html_report",
        # returns one HTML page shell template string; length is inherent HTML verbosity
        "social_research_probe/technologies/report_render/html/raw_html/youtube.py::_page_shell",
        # each runs one statistical algorithm; mathematical code is inherently verbose
        "social_research_probe/technologies/statistics/bayesian_linear.py::run",
        "social_research_probe/technologies/statistics/correlation.py::run",
        "social_research_probe/technologies/statistics/descriptive.py::run",
        "social_research_probe/technologies/statistics/multi_regression.py::run",
        "social_research_probe/technologies/statistics/regression.py::run",
        # timing decorator factory: must handle both sync and async function variants
        "social_research_probe/utils/display/progress.py::log_with_time",
        "social_research_probe/utils/display/progress.py::decorator",
        # subprocess execution with timeout, retry, and streaming; one operation
        "social_research_probe/utils/io/subprocess_runner.py::run",
        # builds one fallback report summary dict with many required fields
        "social_research_probe/utils/report/formatter.py::build_fallback_report_summary",
    }
)


def _production_files() -> list[Path]:
    return sorted(Path("social_research_probe").rglob("*.py"))


class _FunctionLengthVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self._path = path
        self._class_stack: list[str] = []
        self.offenders: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _docstring_line_count(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        if not node.body:
            return 0

        first_stmt = node.body[0]
        if not (
            isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str)
        ):
            return 0

        end_lineno = first_stmt.end_lineno or first_stmt.lineno
        return end_lineno - first_stmt.lineno + 1

    def _check(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end = node.end_lineno or node.lineno
        raw_length = end - node.lineno + 1
        length = raw_length - self._docstring_line_count(node)

        qual = f"{self._class_stack[-1]}.{node.name}" if self._class_stack else node.name
        key = f"{self._path}::{qual}"

        if length > _LIMIT and key not in _WHITELIST:
            self.offenders.append(
                f"{self._path}:{node.lineno} {qual!r} ({length} lines, excluding docstring)"
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)


def test_no_oversized_functions() -> None:
    """Fail when any production function or method exceeds 50 lines."""
    offenders: list[str] = []
    for path in _production_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = _FunctionLengthVisitor(str(path))
        visitor.visit(tree)
        offenders.extend(visitor.offenders)
    assert offenders == [], (
        f"Functions exceeding {_LIMIT} lines (Engineering Rules §Size):\n" + "\n".join(offenders)
    )
