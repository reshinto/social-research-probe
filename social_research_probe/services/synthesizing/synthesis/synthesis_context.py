"""Re-export shim — logic lives in technologies/synthesizing/synthesis_context.py."""

from social_research_probe.technologies.synthesizing.synthesis_context import (  # noqa: F401
    _build_coverage,
    _build_item,
    _fetched_from_highlights,
    build_synthesis_context,
)

__all__ = ["build_synthesis_context"]
