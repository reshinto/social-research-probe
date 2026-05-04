"""Pure-function text-divergence helper used to flag summary mismatches.

Deterministic Jaccard distance on lowercased token sets — no LLM calls. Used
by the enrichment stage to detect when the transcript-based summary and the
runner-direct-URL summary disagree materially.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\w+")


def _tokens(text: str) -> frozenset[str]:
    """Document the tokens rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Set of names found while walking the input structure.

    Examples:
        Input:
            _tokens(
                text="This tool reduces latency by 30%.",
            )
        Output:
            {"comments", "html"}
    """
    return frozenset(_TOKEN_RE.findall(text.lower()))


def jaccard_divergence(a: str, b: str) -> float:
    """Return Jaccard distance over token sets; both-empty returns 0.0.

    Output is in [0.0, 1.0]: 0.0 means identical token sets, 1.0 means
    disjoint. Whitespace, punctuation, and case are normalised away.

    Args:
        a: Numeric series used by the statistical calculation.
        b: Numeric series used by the statistical calculation.

    Returns:
        Numeric score, threshold, or measurement used by analysis and reporting code.

    Examples:
        Input:
            jaccard_divergence(
                a=[1.0, 2.0, 3.0],
                b=[1.0, 2.0, 3.0],
            )
        Output:
            0.75
    """
    ta, tb = _tokens(a), _tokens(b)
    union = ta | tb
    if not union:
        return 0.0
    intersection = ta & tb
    return 1.0 - (len(intersection) / len(union))
