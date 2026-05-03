"""Claim extraction technology: deterministic pattern-based claim extraction."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.claims.types import ExtractedClaim


def _pick_text(data: dict) -> tuple[str, str]:
    surrogate = data.get("text_surrogate") or {}
    primary = str(surrogate.get("primary_text") or "")
    if primary:
        return primary, str(surrogate.get("primary_text_source") or "title")
    transcript = str(data.get("transcript") or "")
    if transcript:
        return transcript, "transcript"
    summary = str(data.get("summary") or "")
    if summary:
        return summary, "summary"
    return "", "title"


def _pick_source_meta(data: dict) -> tuple[str, str, str, str]:
    surrogate = data.get("text_surrogate") or {}
    source_id = str(surrogate.get("source_id") or data.get("id") or "")
    source_url = str(data.get("url") or "")
    source_title = str(data.get("title") or "")
    evidence_tier = str(
        surrogate.get("evidence_tier") or data.get("evidence_tier") or "metadata_only"
    )
    return source_id, source_url, source_title, evidence_tier


def _load_claims_config() -> tuple[int, int, bool]:
    raw = load_active_config().raw
    claims = ((raw.get("platforms") or {}).get("youtube") or {}).get("claims") or {}
    return (
        int(claims.get("max_claims_per_source", 10)),
        int(claims.get("max_claim_chars", 500)),
        bool(claims.get("use_llm", False)),
    )


class ClaimExtractionTech(BaseTechnology[dict, list[ExtractedClaim]]):
    """Extract structured claims from item primary text using deterministic rules."""

    name: ClassVar[str] = "claim_extractor"
    enabled_config_key: ClassVar[str] = "claim_extractor"

    async def _execute(self, data: dict) -> list[ExtractedClaim]:
        from social_research_probe.utils.claims.extractor import extract_claims_auto

        text, evidence_layer = _pick_text(data)
        if not text:
            return []
        source_id, source_url, source_title, evidence_tier = _pick_source_meta(data)
        max_claims, max_chars, use_llm = _load_claims_config()
        return await extract_claims_auto(
            text,
            source_id,
            source_url,
            source_title,
            evidence_layer,
            evidence_tier,
            max_claims=max_claims,
            max_chars=max_chars,
            use_llm=use_llm,
        )
