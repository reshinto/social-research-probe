"""Deterministic narrative ID generation."""

from __future__ import annotations

import hashlib


def derive_narrative_id(claim_ids: list[str]) -> str:
    """Derive a stable narrative ID from sorted claim IDs.

    Args:
        claim_ids: Claim identifiers belonging to this cluster.

    Returns:
        16-character hex string derived from sha256 of sorted, joined claim IDs.
    """
    payload = "|".join(sorted(claim_ids))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
