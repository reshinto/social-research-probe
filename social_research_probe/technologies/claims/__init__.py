"""Claim extraction technology: deterministic pattern-based claim extraction."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.technologies import BaseTechnology
from social_research_probe.utils.claims.types import ExtractedClaim


def _pick_text(data: dict) -> tuple[str, str]:
    """Document the pick text rule at the boundary where callers use it.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _pick_text(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
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
    """Document the pick source meta rule at the boundary where callers use it.

    Args:
        data: Input payload at this service, technology, or pipeline boundary.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _pick_source_meta(
                data={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            ("AI safety", "Find unmet needs")
    """
    surrogate = data.get("text_surrogate") or {}
    source_id = str(surrogate.get("source_id") or data.get("id") or "")
    source_url = str(data.get("url") or "")
    source_title = str(data.get("title") or "")
    evidence_tier = str(
        surrogate.get("evidence_tier") or data.get("evidence_tier") or "metadata_only"
    )
    return source_id, source_url, source_title, evidence_tier


def _load_claims_config() -> tuple[int, int, bool]:
    """Load claims config from disk or active configuration.

    Extraction, review, corroboration, and reporting all need the same claim shape.

    Returns:
        Tuple whose positions are part of the public helper contract shown in the example.

    Examples:
        Input:
            _load_claims_config()
        Output:
            ("AI safety", "Find unmet needs")
    """
    raw = load_active_config().raw
    claims = ((raw.get("platforms") or {}).get("youtube") or {}).get("claims") or {}
    return (
        int(claims.get("max_claims_per_source", 10)),
        int(claims.get("max_claim_chars", 500)),
        bool(claims.get("use_llm", False)),
    )


class ClaimExtractionTech(BaseTechnology[dict, list[ExtractedClaim]]):
    """Extract structured claims from item primary text using deterministic rules.

    Examples:
        Input:
            ClaimExtractionTech
        Output:
            ClaimExtractionTech
    """

    name: ClassVar[str] = "claim_extractor"
    enabled_config_key: ClassVar[str] = "claim_extractor"

    async def _execute(self, data: dict) -> list[ExtractedClaim]:
        """Run this component and return the project-shaped output expected by its service.

        Args:
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _execute(
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
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
