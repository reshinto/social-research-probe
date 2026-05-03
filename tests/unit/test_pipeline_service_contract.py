"""Regression tests for service invocation rules in platform pipelines."""

import ast
from pathlib import Path

YOUTUBE_PACKAGE = Path("social_research_probe/platforms/youtube")
SERVICES_DIR = Path("social_research_probe/services")
DISALLOWED_PIPELINE_SERVICE_CALLS = {
    "classify_batch",
    "score_and_rank",
    "enrich_batch",
    "corroborate_batch",
    "render_charts",
    "execute_one",
    "execute_service",
    "write_report",
}
DISALLOWED_SERVICE_HELPERS = {
    "classify_batch",
    "score_and_rank",
    "enrich_batch",
    "corroborate_batch",
    "render_charts",
    "write_report",
}


def _youtube_trees() -> list[ast.AST]:
    return [
        ast.parse(path.read_text(encoding="utf-8"))
        for path in YOUTUBE_PACKAGE.glob("*.py")
        if path.name != "__init__.py"
    ]


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
        return base.value.id
    return ""


def test_youtube_pipeline_invokes_services_through_execute_batch():
    """Pipeline stages must call service.execute_batch directly.

    Service-specific helpers and direct execute_one calls hide the standard
    BaseService batch lifecycle at the stage boundary. Keeping this rule in a
    test makes accidental bypasses fail in CI instead of relying on code review.
    """
    calls = [
        node.attr
        for tree in _youtube_trees()
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in DISALLOWED_PIPELINE_SERVICE_CALLS
    ]
    assert calls == []


def test_youtube_pipeline_uses_execute_batch_for_service_calls():
    calls = [
        node.attr
        for tree in _youtube_trees()
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "execute_batch"
    ]
    assert calls


def test_service_subclasses_do_not_override_protected_lifecycle_methods():
    forbidden: list[str] = []
    for path in SERVICES_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            for fn in (node for node in cls.body if isinstance(node, ast.AsyncFunctionDef)):
                if fn.name in {"execute_one", "execute_batch"} and cls.name != "BaseService":
                    forbidden.append(f"{path}:{cls.name}.{fn.name}")
    assert forbidden == []


def test_service_subclasses_implement_execute_service_contract():
    missing: list[str] = []
    for path in SERVICES_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            bases = {_base_name(base) for base in cls.bases} & {"BaseService", "FallbackService"}
            if not bases or cls.name in {"BaseService", "FallbackService"}:
                continue
            has_execute_service = any(
                isinstance(node, ast.AsyncFunctionDef) and node.name == "execute_service"
                for node in cls.body
            )
            if not has_execute_service and "FallbackService" not in bases:
                missing.append(f"{path}:{cls.name}")
    assert missing == []


def test_service_subclasses_define_non_empty_technology_contract():
    missing_or_empty: list[str] = []
    for path in SERVICES_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            bases = {_base_name(base) for base in cls.bases} & {"BaseService", "FallbackService"}
            if not bases or cls.name in {"BaseService", "FallbackService"}:
                continue
            get_tech = next(
                (
                    node
                    for node in cls.body
                    if isinstance(node, ast.FunctionDef) and node.name == "_get_technologies"
                ),
                None,
            )
            if get_tech is None:
                missing_or_empty.append(f"{path}:{cls.name}._get_technologies")
                continue
            for return_node in (
                node for node in ast.walk(get_tech) if isinstance(node, ast.Return)
            ):
                if isinstance(return_node.value, ast.List) and not return_node.value.elts:
                    missing_or_empty.append(f"{path}:{cls.name}._get_technologies")
    assert missing_or_empty == []


def test_service_subclasses_do_not_call_protected_technology_runner():
    forbidden: list[str] = []
    for path in SERVICES_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            if cls.name == "BaseService":
                continue
            for attr in (
                node
                for node in ast.walk(cls)
                if isinstance(node, ast.Attribute)
                and node.attr == "_execute_technologies_concurrently"
            ):
                forbidden.append(f"{path}:{cls.name}:{attr.attr}")
    assert forbidden == []


def test_service_subclasses_do_not_keep_stale_stage_helper_methods():
    stale: list[str] = []
    for path in SERVICES_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
            bases = {_base_name(base) for base in cls.bases} & {"BaseService", "FallbackService"}
            if not bases:
                continue
            for fn in (
                node
                for node in cls.body
                if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
            ):
                if fn.name in DISALLOWED_SERVICE_HELPERS:
                    stale.append(f"{path}:{cls.name}.{fn.name}")
    assert stale == []
