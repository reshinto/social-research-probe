"""Purpose composition. Deterministic, pure."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.types import PurposeEntry


@dataclass(frozen=True)
class MergedPurpose:
    """Deterministic merged view of one or more named purposes.

    Examples:
        Input:
            MergedPurpose
        Output:
            MergedPurpose
    """

    names: tuple[str, ...]
    method: str
    evidence_priorities: tuple[str, ...]
    scoring_overrides: Mapping[str, float] = field(default_factory=dict)


def merge_purposes(purposes: dict[str, PurposeEntry], selected: list[str]) -> MergedPurpose:
    """Merge purposes using the module's precedence rules.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        purposes: Purpose name or purpose definitions that shape the research goal.
        selected: Selected purpose definitions requested by the user.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            merge_purposes(
                purposes=[{"name": "Opportunity Map"}],
                selected=["AI safety"],
            )
        Output:
            "AI safety"
    """
    missing = [n for n in selected if n not in purposes]
    if missing:
        raise ValidationError(f"unknown purpose(s): {missing}")

    method_lines: list[str] = []
    seen_methods: set[str] = set()
    evidence: list[str] = []
    seen_evidence: set[str] = set()
    overrides: dict[str, float] = {}

    for name in selected:
        entry = purposes[name]
        method = entry.get("method")
        if method is None:
            raise ValidationError(f"purpose {name!r} is missing required key 'method'")
        if method not in seen_methods:
            method_lines.append(method)
            seen_methods.add(method)
        for pri in entry.get("evidence_priorities", []):
            if pri not in seen_evidence:
                evidence.append(pri)
                seen_evidence.add(pri)
        for key, val in entry.get("scoring_overrides", {}).items():
            if key not in overrides or val > overrides[key]:
                overrides[key] = float(val)

    return MergedPurpose(
        names=tuple(selected),
        method="\n".join(method_lines),
        evidence_priorities=tuple(evidence),
        scoring_overrides=MappingProxyType(overrides),
    )
