"""LLM service package with lazy public exports."""

from __future__ import annotations

import importlib

__all__ = [
    "LLMService",
    "LLMTech",
    "classify_query",
    "emit_report",
]


def __getattr__(name: str) -> object:
    if name in {"LLMService", "LLMTech"}:
        from social_research_probe.services.llm import core

        return getattr(core, name)
    if name == "classify_query":
        from social_research_probe.services.llm.core.classify_query import classify_query

        return classify_query
    if name == "emit_report":
        from social_research_probe.services.llm.core.output import emit_report

        return emit_report
    if name in {"ensemble", "registry", "schemas"}:
        return importlib.import_module(f"social_research_probe.utils.llm.{name}")
    raise AttributeError(name)
