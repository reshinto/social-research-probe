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
    """Return (sentence, char_offset) pairs from text.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _split_sentences(
                text="This tool reduces latency by 30%.",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Return whether is question is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_question(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    return s.rstrip().endswith("?")


def _is_prediction(s: str) -> bool:
    """Return whether is prediction is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_prediction(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower()
    return bool(re.search(r"\b(will|going to|expect|predict|forecast)\b", low))


def _is_recommendation(s: str) -> bool:
    """Return whether is recommendation is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_recommendation(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower().lstrip()
    return bool(re.match(r"(should|must|need to|recommend)\b", low))


def _is_objection(s: str) -> bool:
    """Return whether is objection is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_objection(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower()
    return bool(re.search(r"\b(however|although|despite|problem)\b", low))


def _is_pain_point(s: str) -> bool:
    """Return whether is pain point is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_pain_point(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower()
    return bool(re.search(r"\b(struggle|difficult|challenge|pain|frustrating)\b", low))


def _is_experience(s: str) -> bool:
    """Return whether is experience is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_experience(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower()
    return bool(re.search(r"(i've been|we tried|in my experience|years of|worked with)", low))


def _is_market_signal(s: str) -> bool:
    """Return whether is market signal is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_market_signal(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower()
    return bool(re.search(r"\b(growing|declining|market|adoption|industry|demand|trend)\b", low))


def _is_opinion(s: str) -> bool:
    """Return whether is opinion is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_opinion(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
    low = s.lower()
    return bool(re.search(r"\b(i think|i believe|in my opinion|personally)\b", low))


def _is_fact_claim(s: str) -> bool:
    """Return whether is fact claim is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        s: Source text, prompt text, or raw value being parsed, normalized, classified, or sent to a
           provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_fact_claim(
                s="This tool reduces latency by 30%.",
            )
        Output:
            True
    """
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
    """Assign a claim category to one sentence.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        sentence: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _classify_sentence(
                sentence="This tool reduces latency by 30%.",
            )
        Output:
            "AI safety"
    """
    for predicate, claim_type in _RULES:
        if predicate(sentence):
            return claim_type
    return None


def _extract_entities(sentence: str) -> list[str]:
    """Extract entities from the supplied content.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        sentence: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _extract_entities(
                sentence="This tool reduces latency by 30%.",
            )
        Output:
            ["AI safety", "model evaluation"]
    """
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
    """Derive claim ID from stable fields.

    Extraction, review, corroboration, and reporting all need the same claim shape.

    Args:
        source_id: Stable source identifier or URL used to join records across stages and exports.
        claim_text: Claim text or claim dictionary being extracted, classified, reviewed, or
                    corroborated.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _derive_claim_id(
                source_id="youtube:abc123",
                claim_text={"text": "The model reduces latency by 30%."},
            )
        Output:
            "AI safety"
    """
    digest = hashlib.sha256(f"{source_id}|{claim_text}".encode()).hexdigest()
    return digest[:16]


def _extract_context(
    text: str, position: int, sentence_len: int = 0, width: int = 50
) -> tuple[str, str]:
    """Extract context from the supplied content.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        position: Count, database id, index, or limit that bounds the work being performed.
        sentence_len: Count, database id, index, or limit that bounds the work being performed.
        width: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _extract_context(
                text="This tool reduces latency by 30%.",
                position=3,
                sentence_len=3,
                width=3,
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Build build claim in the shape consumed by the next project step.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        sentence: Source text, prompt text, or raw value being parsed, normalized, classified, or
                  sent to a provider.
        position: Count, database id, index, or limit that bounds the work being performed.
        claim_type: Claim text or claim dictionary being extracted, classified, reviewed, or
                    corroborated.
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        source_id: Stable source identifier or URL used to join records across stages and exports.
        source_url: Stable source identifier or URL used to join records across stages and exports.
        source_title: Human-readable source title stored with extracted claims or citations.
        evidence_layer: Evidence provenance label written with extracted claims.
        evidence_tier: Evidence provenance label written with extracted claims.
        extracted_at: Timestamp used for recency filtering, age calculations, or persisted audit
                      metadata.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _build_claim(
                sentence="This tool reduces latency by 30%.",
                position=3,
                claim_type={"text": "The model reduces latency by 30%."},
                text="This tool reduces latency by 30%.",
                source_id="youtube:abc123",
                source_url="https://youtu.be/abc123",
                source_title="Example video",
                evidence_layer="transcript",
                evidence_tier="direct",
                extracted_at="2026-01-01T00:00:00Z",
            )
        Output:
            "AI safety"
    """
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
    """Extract structured claims from text using deterministic pattern rules.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        source_id: Stable source identifier or URL used to join records across stages and exports.
        source_url: Stable source identifier or URL used to join records across stages and exports.
        source_title: Human-readable source title stored with extracted claims or citations.
        evidence_layer: Evidence provenance label written with extracted claims.
        evidence_tier: Evidence provenance label written with extracted claims.
        max_claims: Count, database id, index, or limit that bounds the work being performed.
        max_chars: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            extract_claims_deterministic(
                text="This tool reduces latency by 30%.",
                source_id="youtube:abc123",
                source_url="https://youtu.be/abc123",
                source_title="Example video",
                evidence_layer="transcript",
                evidence_tier="direct",
                max_claims={"text": "The model reduces latency by 30%."},
                max_chars=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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


async def extract_claims_auto(
    text: str,
    source_id: str,
    source_url: str,
    source_title: str,
    evidence_layer: str,
    evidence_tier: str,
    max_claims: int = 10,
    max_chars: int = 500,
    *,
    use_llm: bool = False,
) -> list[ExtractedClaim]:
    """Route to LLM or deterministic extraction; always falls back to deterministic.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        text: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
              to a provider.
        source_id: Stable source identifier or URL used to join records across stages and exports.
        source_url: Stable source identifier or URL used to join records across stages and exports.
        source_title: Human-readable source title stored with extracted claims or citations.
        evidence_layer: Evidence provenance label written with extracted claims.
        evidence_tier: Evidence provenance label written with extracted claims.
        max_claims: Count, database id, index, or limit that bounds the work being performed.
        max_chars: Count, database id, index, or limit that bounds the work being performed.
        use_llm: Flag that selects the branch for this operation.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            await extract_claims_auto(
                text="This tool reduces latency by 30%.",
                source_id="youtube:abc123",
                source_url="https://youtu.be/abc123",
                source_title="Example video",
                evidence_layer="transcript",
                evidence_tier="direct",
                max_claims={"text": "The model reduces latency by 30%."},
                max_chars=3,
                use_llm=True,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    if not text or not text.strip():
        return []
    if use_llm:
        try:
            from social_research_probe.utils.claims.llm_extractor import extract_claims_llm

            result = await extract_claims_llm(
                text,
                source_id,
                source_url,
                source_title,
                evidence_layer,
                evidence_tier,
                max_claims=max_claims,
                max_chars=max_chars,
            )
            if result:
                return result
        except Exception:
            pass
    return extract_claims_deterministic(
        text,
        source_id,
        source_url,
        source_title,
        evidence_layer,
        evidence_tier,
        max_claims=max_claims,
        max_chars=max_chars,
    )
