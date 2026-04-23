"""Import all LLM runner implementations to trigger their @register decorators.

Runner classes have moved to technologies.llms.*. This module re-imports them
so the registry is fully populated when llm.runners is imported, preserving
backward compatibility for all existing callers.
"""

from __future__ import annotations

import social_research_probe.technologies.llms.claude_cli
import social_research_probe.technologies.llms.codex_cli
import social_research_probe.technologies.llms.gemini_cli
