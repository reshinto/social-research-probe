"""Judge-LLM rubric scoring for the reliability harness.

The judge runner must be **different** from the generator runner — asking
the same model to grade its own output produces correlated errors and
inflates reliability scores. When only one runner is available, the
harness skips the judge step entirely rather than degrade to self-judging.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


RUBRIC_AXES: tuple[str, ...] = ("faithfulness", "completeness", "clarity", "conciseness")


@dataclass
class JudgeScores:
    """Per-axis 1-5 integer scores plus a one-line justification."""

    faithfulness: int
    completeness: int
    clarity: int
    conciseness: int
    justification: str


def build_judge_prompt(summary: str, reference: str) -> str:
    """Construct the rubric prompt sent to the judge LLM."""
    return (
        "You are a strict rubric grader. Score the candidate summary against"
        " the reference on four axes, each 1 (poor) to 5 (excellent):\n"
        "- faithfulness: every claim in the summary is supported by the"
        " reference; zero hallucinations score 5, any hallucination caps at 2.\n"
        "- completeness: the summary captures the key facts of the reference.\n"
        "- clarity: the summary reads naturally; no filler or broken sentences.\n"
        "- conciseness: the summary is dense; no padding or redundancy.\n\n"
        "Return ONLY a JSON object, nothing else:\n"
        '{"faithfulness": <1-5>, "completeness": <1-5>, "clarity": <1-5>,'
        ' "conciseness": <1-5>, "justification": "<one sentence>"}\n\n'
        f"REFERENCE:\n{reference}\n\n"
        f"CANDIDATE:\n{summary}"
    )


def parse_judge_reply(raw: str) -> JudgeScores | None:
    """Parse the judge LLM's JSON response. Returns None on malformed output."""
    # Strip markdown fence if present.
    stripped = re.sub(
        r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.DOTALL
    )
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return JudgeScores(
            faithfulness=_score(payload.get("faithfulness")),
            completeness=_score(payload.get("completeness")),
            clarity=_score(payload.get("clarity")),
            conciseness=_score(payload.get("conciseness")),
            justification=str(payload.get("justification", "")),
        )
    except ValueError:
        return None


def _score(value: object) -> int:
    """Coerce a judge score into an int ∈ [1, 5]. Raises ValueError on bad shapes."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"score is not numeric: {value!r}")
    iv = int(value)
    if not 1 <= iv <= 5:
        raise ValueError(f"score out of range: {iv}")
    return iv
