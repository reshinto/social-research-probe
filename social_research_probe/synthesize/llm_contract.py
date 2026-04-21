"""synthesize/llm_contract.py — Prompt building and response parsing for LLM synthesis.

The pipeline produces a raw evidence packet (via synthesize.formatter.build_packet).
This module's job is to:
  1. Turn that packet into a prompt the LLM can respond to (build_synthesis_prompt).
  2. Parse and validate the LLM's JSON response (parse_synthesis_response).

Called by: CLI and report-generation paths that request structured synthesis.
"""

from __future__ import annotations

import json
from typing import Final

from social_research_probe.errors import ValidationError
from social_research_probe.llm.prompts import SYNTHESIS_PROMPT
from social_research_probe.synthesize.synthesis_context import build_synthesis_context

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
    },
    "required": ["compiled_synthesis", "opportunity_analysis"],
    "additionalProperties": False,
}


def build_synthesis_prompt(packet: dict) -> str:
    """Build the LLM prompt for synthesising an evidence packet.

    Formats SYNTHESIS_PROMPT with topic, platform, a JSON summary of the
    top-N items as evidence, and the structured JSON schema expected back from
    the runner.

    Args:
        packet: A dict produced by synthesize.formatter.build_packet.

    Returns:
        A formatted prompt string ready to send to an LLMRunner.

    Example:
        prompt = build_synthesis_prompt(packet)
        result = runner.run(prompt, schema=RESPONSE_SCHEMA)
    """
    context = build_synthesis_context(packet)
    # Pass the compact synthesis context as the evidence body. It already
    # contains items, stats highlights, chart takeaways, coverage, warnings —
    # everything the LLM should ground its synthesis in.
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

    Checks that both required keys are present and are plain strings.
    If either check fails the caller gets a clear ValidationError rather
    than a cryptic KeyError or type coercion downstream.

    Args:
        raw: The dict returned by LLMRunner.run().

    Returns:
        Dict with exactly two keys: 'compiled_synthesis' and
        'opportunity_analysis', both strings.

    Raises:
        ValidationError: If either required key is missing or not a string.
    """
    out = {}
    for key in ("compiled_synthesis", "opportunity_analysis"):
        val = raw.get(key)
        if not isinstance(val, str):
            raise ValidationError(f"LLM response missing or non-string key: {key!r}")
        out[key] = val
    return out
