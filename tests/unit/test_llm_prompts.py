"""Tests for the LLM prompt templates in llm/prompts.py.

Verifies that each template contains the expected format placeholders and that
.format() can be called successfully with the required keyword arguments.

Who calls it: pytest, run as part of the unit test suite.
"""
from __future__ import annotations

from social_research_probe.llm.prompts import CORROBORATION_PROMPT, SYNTHESIS_PROMPT


def test_synthesis_prompt_has_required_placeholders() -> None:
    """SYNTHESIS_PROMPT contains all four required format placeholders.

    The pipeline fills in {topic}, {platform}, {evidence}, and {schema}
    before sending the prompt to the LLM runner.
    """
    assert "{topic}" in SYNTHESIS_PROMPT
    assert "{platform}" in SYNTHESIS_PROMPT
    assert "{evidence}" in SYNTHESIS_PROMPT
    assert "{schema}" in SYNTHESIS_PROMPT


def test_corroboration_prompt_has_required_placeholders() -> None:
    """CORROBORATION_PROMPT contains both required format placeholders.

    The corroboration host fills in {claim} and {sources} before calling run().
    """
    assert "{claim}" in CORROBORATION_PROMPT
    assert "{sources}" in CORROBORATION_PROMPT


def test_synthesis_prompt_format() -> None:
    """SYNTHESIS_PROMPT.format() succeeds with all required keyword arguments.

    Calling .format() with the expected kwargs must produce a non-empty string
    with no remaining unresolved placeholders.
    """
    filled = SYNTHESIS_PROMPT.format(
        topic="AI",
        platform="youtube",
        evidence="some evidence text",
        schema='{"type": "object"}',
    )
    # The result should be a plain string with the values substituted in.
    assert "AI" in filled
    assert "youtube" in filled
    # No unreplaced placeholders should remain.
    assert "{topic}" not in filled
    assert "{platform}" not in filled
    assert "{evidence}" not in filled
    assert "{schema}" not in filled
