"""Contract: the bundled skill uses host-LLM fallback unless a runner is configured."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_MANIFEST = ROOT / "social_research_probe" / "skill" / "SKILL.md"
RESEARCH_REFERENCE = ROOT / "social_research_probe" / "skill" / "references" / "research.md"


def test_skill_manifest_allows_host_model_invocation() -> None:
    text = SKILL_MANIFEST.read_text(encoding="utf-8")
    assert "disable-model-invocation" not in text


def test_skill_manifest_documents_runner_override_rule() -> None:
    text = SKILL_MANIFEST.read_text(encoding="utf-8")
    assert "When `llm.runner = none`, use the host LLM" in text
    assert "do not duplicate it with the host model" in text


def test_research_reference_documents_host_llm_fallback() -> None:
    text = RESEARCH_REFERENCE.read_text(encoding="utf-8")
    assert "If the user gave a natural-language query and `llm.runner = none`" in text
    assert "use the host LLM to write sections 10-11 inline from the packet" in text
