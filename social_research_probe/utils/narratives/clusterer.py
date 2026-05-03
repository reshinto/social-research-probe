"""Deterministic narrative clustering via entity co-occurrence and claim-type affinity."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime

from social_research_probe.utils.narratives.id_gen import derive_narrative_id
from social_research_probe.utils.narratives.scoring import (
    compute_confidence,
    compute_opportunity_score,
    compute_risk_score,
)

logger = logging.getLogger(__name__)

_TYPE_MAP: dict[str, str] = {
    "fact_claim": "theme",
    "opinion": "theme",
    "prediction": "prediction",
    "recommendation": "opportunity",
    "experience": "theme",
    "question": "question",
    "objection": "objection",
    "pain_point": "pain_point",
    "market_signal": "market_signal",
}

_HIGH_SIGNAL_TYPES: frozenset[str] = frozenset({"opportunity", "market_signal"})

_MAX_CLAIMS_SAFETY_CAP: int = 500

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "very",
        "just",
        "about",
        "up",
        "than",
        "too",
        "also",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "same",
        "all",
        "each",
        "every",
        "both",
        "few",
        "many",
        "much",
        "any",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "if",
        "because",
        "while",
        "although",
    }
)


def cluster_claims(
    items: list[dict],
    *,
    min_cluster_size: int = 2,
    max_cluster_size: int = 12,
    created_at: str | None = None,
) -> list[dict]:
    """Group claims from items into narrative clusters.

    Uses entity co-occurrence via Union-Find, splits oversized clusters by claim_type,
    and merges singletons into nearest cluster by entity overlap.

    Args:
        items: Pipeline items, each with optional 'extracted_claims' list.
        min_cluster_size: Minimum claims to keep a cluster (unless high-signal).
        max_cluster_size: Split threshold for oversized clusters.

    Returns:
        List of NarrativeCluster dicts, sorted by claim_count descending.
    """
    flat_claims = _flatten_claims(items)
    if not flat_claims:
        return []
    if len(flat_claims) > _MAX_CLAIMS_SAFETY_CAP:
        logger.warning(
            "cluster_claims: input has %d claims (cap=%d); returning empty.",
            len(flat_claims),
            _MAX_CLAIMS_SAFETY_CAP,
        )
        return []

    groups = _group_by_entity_cooccurrence(flat_claims)
    groups = _split_oversized(groups, max_cluster_size)
    groups = _merge_singletons(groups, min_cluster_size)
    groups = _filter_small(groups, min_cluster_size)

    clusters = [_build_cluster(group, created_at=created_at) for group in groups]
    clusters.sort(key=lambda c: c["claim_count"], reverse=True)
    return clusters


def _flatten_claims(items: list[dict]) -> list[dict]:
    """Extract all claims from items, tagging each with source metadata."""
    flat: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = item.get("id") or item.get("url", "")
        source_url = item.get("url", "")
        for claim in item.get("extracted_claims", []):
            if not isinstance(claim, dict) or not claim.get("claim_id"):
                continue
            flat.append({**claim, "_source_id": source_id, "_source_url": source_url})
    return flat


def _group_by_entity_cooccurrence(claims: list[dict]) -> list[list[dict]]:
    """Group claims sharing entities via Union-Find."""
    claim_by_id: dict[str, dict] = {}
    parent: dict[str, str] = {}

    for claim in claims:
        cid = claim["claim_id"]
        claim_by_id[cid] = claim
        parent[cid] = cid

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    entity_index: dict[str, list[str]] = {}
    for claim in claims:
        entities = claim.get("entities") or []
        if entities:
            for entity in entities:
                entity_index.setdefault(entity.lower(), []).append(claim["claim_id"])
        else:
            ct = claim.get("claim_type", "mixed")
            entity_index.setdefault(f"__type__{ct}", []).append(claim["claim_id"])

    for _entity, cids in entity_index.items():
        for i in range(1, len(cids)):
            union(cids[0], cids[i])

    groups: dict[str, list[dict]] = {}
    for cid, claim in claim_by_id.items():
        root = find(cid)
        groups.setdefault(root, []).append(claim)

    return list(groups.values())


def _split_oversized(groups: list[list[dict]], max_size: int) -> list[list[dict]]:
    """Split groups exceeding max_size by claim_type."""
    result: list[list[dict]] = []
    for group in groups:
        if len(group) <= max_size:
            result.append(group)
        else:
            by_type: dict[str, list[dict]] = {}
            for c in group:
                by_type.setdefault(c.get("claim_type", "mixed"), []).append(c)
            result.extend(by_type.values())
    return result


def _merge_singletons(groups: list[list[dict]], min_size: int) -> list[list[dict]]:
    """Merge groups below min_size into nearest large group by entity overlap."""
    large = [g for g in groups if len(g) >= min_size]
    small = [g for g in groups if len(g) < min_size]

    if not large and small:
        all_small_claims = [c for g in small for c in g]
        return [all_small_claims] if all_small_claims else []

    for group in small:
        for claim in group:
            best_overlap = -1
            best_idx = 0
            claim_entities = {e.lower() for e in claim.get("entities") or []}
            for i, lg in enumerate(large):
                group_entities = {e.lower() for c in lg for e in (c.get("entities") or [])}
                overlap = len(claim_entities & group_entities)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_idx = i
            large[best_idx].append(claim)

    return large


def _filter_small(groups: list[list[dict]], min_size: int) -> list[list[dict]]:
    """Remove groups below min_size unless they are high-signal types."""
    result: list[list[dict]] = []
    for group in groups:
        if len(group) >= min_size:
            result.append(group)
            continue
        cluster_type = _resolve_cluster_type(group)
        if cluster_type in _HIGH_SIGNAL_TYPES:
            result.append(group)
    return result


def _resolve_cluster_type(claims: list[dict]) -> str:
    """Majority vote on claim_type mapped to cluster_type."""
    if not claims:
        return "mixed"
    mapped = [_TYPE_MAP.get(c.get("claim_type", ""), "theme") for c in claims]
    counter = Counter(mapped)
    top = counter.most_common(2)
    if len(top) >= 2 and top[0][1] == top[1][1]:
        return "mixed"
    return top[0][0]


def _build_cluster(claims: list[dict], *, created_at: str | None = None) -> dict:
    """Build a NarrativeCluster dict from a group of claims."""
    claim_ids = sorted({c["claim_id"] for c in claims})
    source_ids = sorted({c.get("_source_id", "") for c in claims} - {""})
    source_urls = sorted({c.get("_source_url", "") for c in claims} - {""})

    all_entities: list[str] = []
    for c in claims:
        all_entities.extend(c.get("entities") or [])
    entities = sorted(set(all_entities))

    evidence_tiers = sorted({c.get("evidence_tier", "") for c in claims} - {""})
    corroboration_statuses = sorted({c.get("corroboration_status", "") for c in claims} - {""})

    sorted_by_confidence = sorted(claims, key=lambda c: c.get("confidence", 0), reverse=True)
    representative_claims = [c.get("claim_text", "") for c in sorted_by_confidence[:3]]

    cluster_type = _resolve_cluster_type(claims)
    title = _build_title(cluster_type, entities)
    summary = "; ".join(representative_claims[:2])

    contradiction_count = sum(1 for c in claims if c.get("contradiction_status", "none") != "none")
    needs_review_count = sum(1 for c in claims if c.get("needs_review"))

    keywords = _extract_keywords(claims)

    return {
        "narrative_id": derive_narrative_id(claim_ids),
        "title": title,
        "summary": summary,
        "cluster_type": cluster_type,
        "claim_ids": claim_ids,
        "source_ids": source_ids,
        "source_urls": source_urls,
        "representative_claims": representative_claims,
        "entities": entities,
        "keywords": keywords,
        "evidence_tiers": evidence_tiers,
        "corroboration_statuses": corroboration_statuses,
        "source_count": len(source_ids),
        "claim_count": len(claim_ids),
        "confidence": compute_confidence(claims),
        "opportunity_score": compute_opportunity_score(claims, cluster_type),
        "risk_score": compute_risk_score(claims, cluster_type),
        "contradiction_count": contradiction_count,
        "needs_review_count": needs_review_count,
        "created_at": created_at or datetime.now(tz=UTC).isoformat(),
    }


def _build_title(cluster_type: str, entities: list[str]) -> str:
    """Generate a deterministic title from type and top entities."""
    type_label = cluster_type.replace("_", " ").title()
    if entities:
        top = ", ".join(entities[:3])
        return f"{type_label}: {top}"
    return type_label


def _extract_keywords(claims: list[dict]) -> list[str]:
    """Extract top keywords from claim texts via word frequency."""
    word_counts: Counter[str] = Counter()
    for claim in claims:
        text = claim.get("claim_text", "").lower()
        words = [w.strip(".,;:!?\"'()[]{}") for w in text.split()]
        for word in words:
            if len(word) > 2 and word not in _STOPWORDS and word.isalpha():
                word_counts[word] += 1
    return [word for word, _count in word_counts.most_common(10)]
