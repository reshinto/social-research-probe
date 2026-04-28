"""Re-export shim — logic lives in utils/report/contextual_explain.py."""

from social_research_probe.utils.report.contextual_explain import (
    contextual_explanation,
    infer_model,
    parse_numeric,
)

__all__ = [
    "contextual_explanation",
    "infer_model",
    "parse_numeric",
]
