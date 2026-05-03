"""Deterministic claim extraction from item primary text."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime

from social_research_probe.utils.claims.types import ClaimType, ExtractedClaim

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?")
_ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z]+\b")


def _split_sentences(text: str) -> list[tuple[str, int]]:
    """Return (sentence, char_offset) pairs from text."""
    if not text.strip():
        return []
    results: list[tuple[str, int]] = []
    pos = 0
    for part in _SENTENCE_END.split(text):
        stripped = part.strip()
        if stripped:
            offset = text.find(stripped, pos)
            results.append((stripped, offset))
            pos = offset + len(stripped)
    return results


def _is_question(s: str) -> bool:
    return s.rstrip().endswith("?")


def _is_prediction(s: str) -> bool:
    low = s.lower()
    return bool(re.search(r"\b(will|going to|expect|predict|forecast)\b", low))


def _is_recommendation(s: str) -> bool:
    low = s.lower().lstrip()
    return bool(re.match(r"(should|must|need to|recommend)\b", low))


def _is_objection(s: str) -> bool:
    low = s.lower()
    return bool(re.search(r"\b(however|although|despite|problem)\b", low))


def _is_pain_point(s: str) -> bool:
    low = s.lower()
    return bool(re.search(r"\b(struggle|difficult|challenge|pain|frustrating)\b", low))


def _is_experience(s: str) -> bool:
    low = s.lower()
    return bool(re.search(r"(i've been|we tried|in my experience|years of|worked with)", low))


def _is_market_signal(s: str) -> bool:
    low = s.lower()
    return bool(re.search(r"\b(growing|declining|market|adoption|industry|demand|trend)\b", low))


def _is_opinion(s: str) -> bool:
    low = s.lower()
    return bool(re.search(r"\b(i think|i believe|in my opinion|personally)\b", low))


def _is_fact_claim(s: str) -> bool:
    low = s.lower()
    return bool(_NUMBER_RE.search(s) or re.search(r"\baccording to\b", low))


_RULES: list[tuple[Callable[[str], bool], ClaimType]] = [
    (_is_question, "question"),
    (_is_prediction, "prediction"),
    (_is_recommendation, "recommendation"),
    (_is_objection, "objection"),
    (_is_pain_point, "pain_point"),
    (_is_experience, "experience"),
    (_is_market_signal, "market_signal"),
    (_is_opinion, "opinion"),
    (_is_fact_claim, "fact_claim"),
]

_NEEDS_CORROBORATION: frozenset[ClaimType] = frozenset(
    {"fact_claim", "prediction", "market_signal"}
)


def _classify_sentence(sentence: str) -> ClaimType | None:
    for predicate, claim_type in _RULES:
        if predicate(sentence):
            return claim_type
    return None


def _extract_entities(sentence: str) -> list[str]:
    numbers = _NUMBER_RE.findall(sentence)
    capitalized = _ENTITY_RE.findall(sentence)
    seen: set[str] = set()
    entities: list[str] = []
    for e in numbers + capitalized:
        if e not in seen:
            seen.add(e)
            entities.append(e)
    return entities


def _derive_claim_id(source_id: str, claim_text: str) -> str:
    digest = hashlib.sha256(f"{source_id}|{claim_text}".encode()).hexdigest()
    return digest[:16]


def _extract_context(
    text: str, position: int, sentence_len: int = 0, width: int = 50
) -> tuple[str, str]:
    before_start = max(0, position - width)
    before = text[before_start:position]
    after_start = position + sentence_len
    after_end = min(len(text), after_start + width)
    after = text[after_start:after_end]
    return before, after


def _build_claim(
    *,
    sentence: str,
    position: int,
    claim_type: ClaimType,
    text: str,
    source_id: str,
    source_url: str,
    source_title: str,
    evidence_layer: str,
    evidence_tier: str,
    extracted_at: str,
) -> ExtractedClaim:
    claim_id = _derive_claim_id(source_id, sentence)
    context_before, context_after = _extract_context(text, position, sentence_len=len(sentence))
    return {
        "claim_id": claim_id,
        "source_id": source_id,
        "source_url": source_url,
        "source_title": source_title,
        "claim_text": sentence,
        "evidence_text": sentence,
        "claim_type": claim_type,
        "entities": _extract_entities(sentence),
        "confidence": 0.7,
        "evidence_layer": evidence_layer,
        "evidence_tier": evidence_tier,
        "needs_corroboration": claim_type in _NEEDS_CORROBORATION,
        "corroboration_status": "pending",
        "contradiction_status": "none",
        "needs_review": False,
        "uncertainty": "low",
        "extraction_method": "deterministic",
        "source_sentence": sentence,
        "position_in_text": position,
        "context_before": context_before,
        "context_after": context_after,
        "extracted_at": extracted_at,
    }


def extract_claims_deterministic(
    text: str,
    source_id: str,
    source_url: str,
    source_title: str,
    evidence_layer: str,
    evidence_tier: str,
    max_claims: int = 10,
    max_chars: int = 500,
) -> list[ExtractedClaim]:
    """Extract structured claims from text using deterministic pattern rules."""
    if not text or not text.strip():
        return []
    extracted_at = datetime.now(tz=UTC).isoformat()
    claims: list[ExtractedClaim] = []
    for sentence, position in _split_sentences(text):
        if len(claims) >= max_claims:
            break
        if len(sentence) > max_chars:
            continue
        claim_type = _classify_sentence(sentence)
        if claim_type is None:
            continue
        claims.append(
            _build_claim(
                sentence=sentence,
                position=position,
                claim_type=claim_type,
                text=text,
                source_id=source_id,
                source_url=source_url,
                source_title=source_title,
                evidence_layer=evidence_layer,
                evidence_tier=evidence_tier,
                extracted_at=extracted_at,
            )
        )
    return claims
