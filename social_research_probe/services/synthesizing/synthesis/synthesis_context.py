"""Re-export shim — logic lives in technologies/synthesizing/synthesis_context.py."""

from social_research_probe.technologies.synthesizing.synthesis_context import (
    _build_coverage,
    _build_item,
    _fetched_from_highlights,
    build_synthesis_context,
)

__all__ = [
    "_build_coverage",
    "_build_item",
    "_fetched_from_highlights",
    "build_synthesis_context",
]
