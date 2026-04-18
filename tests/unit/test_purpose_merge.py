"""Purpose merge: union evidence_priorities (preserve order), concat methods,
element-wise-max scoring_overrides (strictest trust wins)."""
from __future__ import annotations

from social_research_probe.purposes.merge import MergedPurpose, merge_purposes


def test_single_purpose_passthrough():
    purposes = {
        "trends": {
            "method": "Track emergence",
            "evidence_priorities": ["view velocity", "recency"],
            "scoring_overrides": {"trust": 0.5},
        }
    }
    merged = merge_purposes(purposes, ["trends"])
    assert merged.method == "Track emergence"
    assert merged.evidence_priorities == ("view velocity", "recency")
    assert merged.scoring_overrides == {"trust": 0.5}


def test_two_purposes_union_evidence_preserve_order():
    purposes = {
        "trends": {"method": "A", "evidence_priorities": ["a", "b"], "scoring_overrides": {}},
        "career": {"method": "B", "evidence_priorities": ["b", "c"], "scoring_overrides": {}},
    }
    merged = merge_purposes(purposes, ["trends", "career"])
    assert merged.evidence_priorities == ("a", "b", "c")


def test_method_concat_dedup():
    purposes = {
        "trends": {"method": "A", "evidence_priorities": [], "scoring_overrides": {}},
        "career": {"method": "B", "evidence_priorities": [], "scoring_overrides": {}},
        "dup": {"method": "A", "evidence_priorities": [], "scoring_overrides": {}},
    }
    merged = merge_purposes(purposes, ["trends", "career", "dup"])
    assert merged.method == "A\nB"  # dup "A" omitted


def test_scoring_overrides_element_wise_max():
    purposes = {
        "lax": {"method": "x", "evidence_priorities": [], "scoring_overrides": {"trust": 0.3, "trend": 0.2}},
        "strict": {"method": "y", "evidence_priorities": [], "scoring_overrides": {"trust": 0.7}},
    }
    merged = merge_purposes(purposes, ["lax", "strict"])
    assert merged.scoring_overrides == {"trust": 0.7, "trend": 0.2}


def test_unknown_purpose_raises():
    import pytest
    from social_research_probe.errors import ValidationError

    with pytest.raises(ValidationError):
        merge_purposes({}, ["nonexistent"])


def test_merged_is_frozen_dataclass():
    purposes = {"p": {"method": "x", "evidence_priorities": [], "scoring_overrides": {}}}
    merged = merge_purposes(purposes, ["p"])
    assert isinstance(merged, MergedPurpose)
    import pytest
    with pytest.raises(Exception):  # frozen
        merged.method = "changed"  # type: ignore[misc]
