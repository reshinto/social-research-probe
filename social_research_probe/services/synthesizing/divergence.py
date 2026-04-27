"""Pure-function text-divergence helper used to flag summary mismatches.

Deterministic Jaccard distance on lowercased token sets — no LLM calls. Used
by the enrichment stage to detect when the transcript-based summary and the
runner-direct-URL summary disagree materially.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\w+")


def _tokens(text: str) -> frozenset[str]:
    """Return the set of lowercase word tokens in ``text``."""
    return frozenset(_TOKEN_RE.findall(text.lower()))


def jaccard_divergence(a: str, b: str) -> float:
    """Return Jaccard distance over token sets; both-empty returns 0.0.

    Output is in [0.0, 1.0]: 0.0 means identical token sets, 1.0 means
    disjoint. Whitespace, punctuation, and case are normalised away.
    """
    ta, tb = _tokens(a), _tokens(b)
    union = ta | tb
    if not union:
        return 0.0
    intersection = ta & tb
    return 1.0 - (len(intersection) / len(union))
