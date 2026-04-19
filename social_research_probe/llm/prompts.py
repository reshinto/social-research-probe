"""Prompt templates for LLM calls made by the pipeline and corroboration host.

Why this exists: centralising prompt strings here keeps them version-controlled
and easy to review, tweak, or A/B-test without touching runner or pipeline code.

Who calls it: synthesize (pipeline step that writes summaries) and the
corroboration host. Callers use .format(**kwargs) to fill in the placeholders.
"""
from __future__ import annotations

# Used by the synthesis step: given collected evidence for a topic on a
# platform, ask the LLM to produce a structured summary.
SYNTHESIS_PROMPT = """\
You are a research analyst. Given the following evidence packet, write a concise synthesis.

Topic: {topic}
Platform: {platform}
Evidence:
{evidence}

Respond in JSON matching the schema: {schema}
"""

# Used by the corroboration host: given a claim and a list of source excerpts,
# ask the LLM to evaluate whether the sources support, refute, or are
# inconclusive about the claim.
CORROBORATION_PROMPT = """\
You are a fact-checker. Evaluate whether the following claim is supported by the provided sources.

Claim: {claim}
Sources:
{sources}

Respond in JSON with keys: verdict (supported|refuted|inconclusive), confidence (0.0-1.0), reasoning (str).
"""
