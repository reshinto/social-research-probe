"""Import all LLM runner implementations to trigger their @register decorators.

Why this exists: Python only executes module-level code (including @register
calls) when a module is imported. Importing all four runners here ensures the
registry is fully populated as soon as `llm.runners` is imported, without
callers needing to know which runner files exist.

Who calls it: llm/__init__.py, which is itself imported by anything that uses
the LLM subsystem.
"""

from __future__ import annotations

import social_research_probe.llm.runners.claude
import social_research_probe.llm.runners.codex
import social_research_probe.llm.runners.gemini
import social_research_probe.llm.runners.local
