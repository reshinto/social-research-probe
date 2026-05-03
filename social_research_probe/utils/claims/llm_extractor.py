"""LLM-backed claim extractor with deterministic fallback on any failure."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import get_args

from social_research_probe.utils.claims.extractor import (
    _NEEDS_CORROBORATION,
    _derive_claim_id,
    _extract_context,
)
from social_research_probe.utils.claims.types import ClaimType, ExtractedClaim

_VALID_CLAIM_TYPES: list[ClaimType] = list(get_args(ClaimType))
_VALID_UNCERTAINTY: frozenset[str] = frozenset({"low", "medium", "high"})
_TEXT_LIMIT = 5000


def _build_claim_extraction_prompt(
    text: str, source_title: str, max_claims: int, max_chars: int
) -> str:
    from social_research_probe.utils.llm.prompts import CLAIM_EXTRACTION_PROMPT

    return CLAIM_EXTRACTION_PROMPT.format(
        max_claims=max_claims,
        source_title=source_title,
        text=text[:_TEXT_LIMIT],
        max_chars=max_chars,
    )


def _preferred_runner() -> str:
    from social_research_probe.config import load_active_config

    return load_active_config().llm_runner


def _run_llm(prompt: str) -> object:
    from social_research_probe.utils.llm.registry import run_with_fallback
    from social_research_probe.utils.llm.schemas import CLAIM_EXTRACTION_SCHEMA

    return run_with_fallback(prompt, schema=CLAIM_EXTRACTION_SCHEMA, preferred=_preferred_runner())


def _extract_json_object(response: object) -> dict | None:
    if isinstance(response, dict):
        return response
    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except (json.JSONDecodeError, ValueError):
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def _coerce_claim_type(value: object) -> ClaimType | None:
    for ct in _VALID_CLAIM_TYPES:
        if value == ct:
            return ct
    return None


def _coerce_confidence(value: object) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value)))
    return 0.75


def _coerce_entities(value: object) -> list[str]:
    if isinstance(value, list):
        return [e for e in value if isinstance(e, str)]
    return []


def _derive_uncertainty(confidence: float) -> str:
    if confidence >= 0.8:
        return "low"
    if confidence >= 0.5:
        return "medium"
    return "high"


def _coerce_raw_claim(
    raw: dict,
    max_chars: int,
) -> tuple[str, ClaimType, float, list[str], str, bool] | None:
    """Validate and coerce fields from a raw LLM claim dict. Returns None if invalid."""
    claim_text: str = raw.get("claim_text") or ""
    if not isinstance(claim_text, str) or not claim_text.strip():
        return None
    claim_text = claim_text[:max_chars]
    claim_type = _coerce_claim_type(raw.get("claim_type"))
    if claim_type is None:
        return None
    confidence = _coerce_confidence(raw.get("confidence"))
    entities = _coerce_entities(raw.get("entities"))
    raw_uncertainty = raw.get("uncertainty")
    uncertainty = (
        raw_uncertainty
        if isinstance(raw_uncertainty, str) and raw_uncertainty in _VALID_UNCERTAINTY
        else _derive_uncertainty(confidence)
    )
    raw_corrob = raw.get("needs_corroboration")
    needs_corroboration = (
        bool(raw_corrob) if isinstance(raw_corrob, bool) else claim_type in _NEEDS_CORROBORATION
    )
    return (claim_text, claim_type, confidence, entities, uncertainty, needs_corroboration)


def _normalize_llm_claim(
    raw_claim: object,
    *,
    source_id: str,
    source_url: str,
    source_title: str,
    evidence_layer: str,
    evidence_tier: str,
    text: str,
    extracted_at: str,
    max_chars: int,
) -> ExtractedClaim | None:
    if not isinstance(raw_claim, dict):
        return None
    coerced = _coerce_raw_claim(raw_claim, max_chars)
    if coerced is None:
        return None
    claim_text, claim_type, confidence, entities, uncertainty, needs_corroboration = coerced
    claim_id = _derive_claim_id(source_id, claim_text)
    position = text.find(claim_text)
    if position == -1:
        position = 0
    context_before, context_after = _extract_context(text, position, sentence_len=len(claim_text))
    return {
        "claim_id": claim_id,
        "source_id": source_id,
        "source_url": source_url,
        "source_title": source_title,
        "claim_text": claim_text,
        "evidence_text": claim_text,
        "claim_type": claim_type,
        "entities": entities,
        "confidence": confidence,
        "evidence_layer": evidence_layer,
        "evidence_tier": evidence_tier,
        "needs_corroboration": needs_corroboration,
        "corroboration_status": "pending",
        "contradiction_status": "none",
        "needs_review": confidence < 0.8,
        "uncertainty": uncertainty,
        "extraction_method": "llm",
        "source_sentence": claim_text,
        "position_in_text": position,
        "context_before": context_before,
        "context_after": context_after,
        "extracted_at": extracted_at,
    }


def _collect_claims(
    raw_claims: list,
    *,
    source_id: str,
    source_url: str,
    source_title: str,
    evidence_layer: str,
    evidence_tier: str,
    text: str,
    max_claims: int,
    max_chars: int,
) -> list[ExtractedClaim]:
    extracted_at = datetime.now(tz=UTC).isoformat()
    seen_ids: set[str] = set()
    claims: list[ExtractedClaim] = []
    for raw in raw_claims:
        if len(claims) >= max_claims:
            break
        claim = _normalize_llm_claim(
            raw,
            source_id=source_id,
            source_url=source_url,
            source_title=source_title,
            evidence_layer=evidence_layer,
            evidence_tier=evidence_tier,
            text=text,
            extracted_at=extracted_at,
            max_chars=max_chars,
        )
        if claim is None or claim["claim_id"] in seen_ids:
            continue
        seen_ids.add(claim["claim_id"])
        claims.append(claim)
    return claims


async def extract_claims_llm(
    text: str,
    source_id: str,
    source_url: str,
    source_title: str,
    evidence_layer: str,
    evidence_tier: str,
    max_claims: int = 10,
    max_chars: int = 500,
) -> list[ExtractedClaim] | None:
    """Extract claims via LLM. Returns None on any failure (caller should fall back)."""
    if not text or not text.strip():
        return None
    prompt = _build_claim_extraction_prompt(text, source_title, max_claims, max_chars)
    try:
        response = await asyncio.to_thread(_run_llm, prompt)
    except Exception:
        return None
    parsed = _extract_json_object(response)
    if parsed is None:
        return None
    raw_claims = parsed.get("claims")
    if not isinstance(raw_claims, list):
        return None
    claims = _collect_claims(
        raw_claims,
        source_id=source_id,
        source_url=source_url,
        source_title=source_title,
        evidence_layer=evidence_layer,
        evidence_tier=evidence_tier,
        text=text,
        max_claims=max_claims,
        max_chars=max_chars,
    )
    return claims if claims else None
