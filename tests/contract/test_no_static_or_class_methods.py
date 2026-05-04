"""Contract: no @staticmethod or @classmethod in production code.

Pure functions with no class dependency belong as module-level free functions
in utils/. Methods that access class state should be instance methods.

Justified exceptions must be added to _WHITELIST with a comment explaining why.
"""

from __future__ import annotations

import ast
from pathlib import Path

_WHITELIST: frozenset[str] = frozenset(
    {
        # Config.load is a factory constructor — standard Python pattern requires classmethod
        "social_research_probe/config.py::Config.load",
        # BaseService.is_enabled must read cls.enabled_config_key at the class level
        "social_research_probe/services/__init__.py::BaseService.is_enabled",
    }
)


def _production_files() -> list[Path]:
    return sorted(Path("social_research_probe").rglob("*.py"))


_BANNED = frozenset({"staticmethod", "classmethod"})


class _DecoratorVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self._path = path
        self._class_stack: list[str] = []
        self.offenders: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _check(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            name = decorator.id if isinstance(decorator, ast.Name) else None
            if name not in _BANNED:
                continue
            qual = f"{self._class_stack[-1]}.{node.name}" if self._class_stack else node.name
            key = f"{self._path}::{qual}"
            if key not in _WHITELIST:
                self.offenders.append(f"{self._path}:{node.lineno} @{name} on {qual!r}")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check(node)
        self.generic_visit(node)


def test_no_static_or_class_methods() -> None:
    """Fail when any production method uses @staticmethod or @classmethod."""
    offenders: list[str] = []
    for path in _production_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = _DecoratorVisitor(str(path))
        visitor.visit(tree)
        offenders.extend(visitor.offenders)
    assert offenders == [], (
        "Methods using @staticmethod or @classmethod (move to utils/ or use instance method):\n"
        + "\n".join(offenders)
    )
