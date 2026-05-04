"""Prompt building and response parsing for LLM synthesis.

The pipeline produces a raw evidence report (via services.synthesizing.helpers.formatter.build_report).
This module's job is to:
  1. Turn that report into a prompt the LLM can respond to (build_synthesis_prompt).
  2. Parse and validate the LLM's JSON response (parse_synthesis_response).

Called by: CLI and report-generation paths that request structured synthesis.
"""

from __future__ import annotations

import json
from typing import Final

from social_research_probe.technologies.synthesizing.synthesis_context import (
    build_synthesis_context,
)
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.llm.prompts import SYNTHESIS_PROMPT

SYNTHESIS_JSON_SCHEMA: Final[dict] = {
    "type": "object",
    "properties": {
        "compiled_synthesis": {
            "type": "string",
            "description": "Concise synthesis of the evidence, at most 150 words.",
        },
        "opportunity_analysis": {
            "type": "string",
            "description": "Concise opportunity analysis, at most 150 words.",
        },
        "report_summary": {
            "type": "string",
            "description": (
                "Integrated final summary of the report, combining the key "
                "statistics, chart signals, synthesis, and opportunity "
                "analysis, at most 180 words."
            ),
        },
    },
    "required": ["compiled_synthesis", "opportunity_analysis", "report_summary"],
    "additionalProperties": False,
}


def build_synthesis_prompt(report: dict) -> str:
    """Build the LLM prompt for synthesising an evidence report.

    Formats SYNTHESIS_PROMPT with topic, platform, a JSON summary of the top-N items as evidence,
    and the structured JSON schema expected back from the runner.

    Args:
        report: Research report dictionary being rendered, exported, or persisted.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            build_synthesis_prompt(
                report={"topic": "AI safety", "items_top_n": []},
            )
        Output:
            "AI safety"
    """
    context = build_synthesis_context(report)
    evidence = json.dumps(context, indent=2)
    schema = json.dumps(SYNTHESIS_JSON_SCHEMA)
    return SYNTHESIS_PROMPT.format(
        topic=context["topic"],
        platform=context["platform"],
        evidence=evidence,
        schema=schema,
    )


def parse_synthesis_response(raw: dict) -> dict:
    """Validate and extract the LLM's synthesis response.

    The helper keeps a small project rule named and documented at the boundary where it is used.

    Args:
        raw: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to
             a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Raises:
                        ValidationError: If either required key is missing or not a string.




    Examples:
        Input:
            parse_synthesis_response(
                raw="42",
            )
        Output:
            {"enabled": True}
    """
    out = {}
    for key in ("compiled_synthesis", "opportunity_analysis", "report_summary"):
        val = raw.get(key)
        if not isinstance(val, str):
            raise ValidationError(f"LLM response missing or non-string key: {key!r}")
        out[key] = val
    return out
