"""synthesize/llm_contract.py — Prompt building and response parsing for LLM synthesis.

The pipeline produces a raw evidence packet (via synthesize.formatter.build_packet).
This module's job is to:
  1. Turn that packet into a prompt the LLM can respond to (build_synthesis_prompt).
  2. Parse and validate the LLM's JSON response (parse_synthesis_response).

Called by: pipeline.run_research (skill mode) and commands/research.py (cli mode).
"""
from __future__ import annotations

import json

from social_research_probe.errors import ValidationError
from social_research_probe.llm.prompts import SYNTHESIS_PROMPT
from social_research_probe.synthesize.formatter import RESPONSE_SCHEMA


def build_synthesis_prompt(packet: dict) -> str:
    """Build the LLM prompt for synthesising an evidence packet.

    Formats SYNTHESIS_PROMPT with topic, platform, a JSON summary of the
    top-5 items as evidence, and the expected response schema.

    Args:
        packet: A dict produced by synthesize.formatter.build_packet.

    Returns:
        A formatted prompt string ready to send to an LLMRunner.

    Example:
        prompt = build_synthesis_prompt(packet)
        result = runner.run(prompt, schema=RESPONSE_SCHEMA)
    """
    # Serialize the top-5 items as pretty-printed JSON so the LLM can parse
    # them as structured evidence rather than a raw Python repr.
    evidence = json.dumps(packet.get("items_top5", []), indent=2)
    # The schema is compact JSON so it fits neatly on one prompt line.
    schema = json.dumps(RESPONSE_SCHEMA)
    return SYNTHESIS_PROMPT.format(
        topic=packet.get("topic", ""),
        platform=packet.get("platform", ""),
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
            raise ValidationError(
                f"LLM response missing or non-string key: {key!r}"
            )
        out[key] = val
    return out
