"""LLM runner registry. Importing this package registers all built-in runners.

Why this exists: the pipeline and corroboration host import this package to
gain access to the registry without needing to manually import each runner
module. The side-effect import of llm.runners populates the registry.

Who calls it: any module that calls llm.registry.get_runner() or
llm.registry.list_runners().
"""
from __future__ import annotations

from social_research_probe.llm import runners  # noqa: F401  — triggers registration
