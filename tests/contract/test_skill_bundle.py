"""Contract: bundled skill is manual and avoids host-LLM fallback docs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_MANIFEST = ROOT / "social_research_probe" / "skill" / "SKILL.md"
RESEARCH_REFERENCE = ROOT / "social_research_probe" / "skill" / "references" / "research.md"


def test_skill_manifest_is_manual_only() -> None:
    text = SKILL_MANIFEST.read_text(encoding="utf-8")
    assert "disable-model-invocation: true" in text


def test_skill_manifest_does_not_document_host_llm_fallback() -> None:
    text = SKILL_MANIFEST.read_text(encoding="utf-8")
    assert "host LLM" not in text
    assert "host model" not in text


def test_research_reference_does_not_document_host_llm_fallback() -> None:
    text = RESEARCH_REFERENCE.read_text(encoding="utf-8")
    assert "host LLM" not in text
    assert "host model" not in text
