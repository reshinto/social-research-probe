"""Tests for platforms.orchestrator pure helpers."""

from __future__ import annotations

import pytest

from social_research_probe.platforms import orchestrator
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.research_command_parser import ParsedRunResearch


def test_resolve_purposes_unknown():
    with pytest.raises(ValidationError, match="unknown purpose"):
        orchestrator._resolve_purposes(("missing",), {})


def test_resolve_purposes_basic():
    purposes = {"x": {"method": "M", "evidence_priorities": []}}
    out = orchestrator._resolve_purposes(("x",), purposes)
    assert out.names == ("x",)


def test_build_state_assembles_inputs():
    purposes = {"p1": {"method": "M", "evidence_priorities": []}}
    merged = orchestrator._resolve_purposes(("p1",), purposes)
    cmd = ParsedRunResearch(platform="youtube", topics=[("ai", ["p1"])])
    state = orchestrator._build_state("ai", merged, cmd, {"max_items": 5})
    assert state.platform_type == "youtube"
    assert state.inputs["topic"] == "ai"
    assert state.inputs["purpose_names"] == ["p1"]
    assert state.platform_config["max_items"] == 5
