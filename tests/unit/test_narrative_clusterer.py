"""Tests for deterministic narrative clustering algorithm."""

from __future__ import annotations

from social_research_probe.utils.narratives.clusterer import _resolve_cluster_type, cluster_claims
from social_research_probe.utils.narratives.id_gen import derive_narrative_id


def _item(item_id: str, claims: list[dict]) -> dict:
    return {
        "id": item_id,
        "url": f"https://example.com/{item_id}",
        "extracted_claims": claims,
    }


def _claim(
    claim_id: str,
    claim_type: str = "fact_claim",
    entities: list[str] | None = None,
    confidence: float = 0.7,
    corroboration_status: str = "pending",
    contradiction_status: str = "none",
    needs_review: bool = False,
    claim_text: str = "",
) -> dict:
    return {
        "claim_id": claim_id,
        "claim_text": claim_text or f"Claim {claim_id}",
        "claim_type": claim_type,
        "entities": entities or [],
        "confidence": confidence,
        "evidence_tier": "transcript_rich",
        "corroboration_status": corroboration_status,
        "contradiction_status": contradiction_status,
        "needs_review": needs_review,
        "position_in_text": 1,
        "extracted_at": "2024-01-01T00:00:00",
    }


class TestClusterClaimsEmpty:
    def test_empty_items_returns_empty(self) -> None:
        assert cluster_claims([]) == []

    def test_no_claims_in_items_returns_empty(self) -> None:
        items = [{"id": "v1", "url": "u", "extracted_claims": []}]
        assert cluster_claims(items) == []

    def test_non_dict_items_skipped(self) -> None:
        assert cluster_claims(["not_a_dict", None, 42]) == []


class TestEntityGrouping:
    def test_claims_sharing_entity_grouped(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"]),
                    _claim("c2", entities=["AI", "ML"]),
                ],
            ),
            _item("v2", [_claim("c3", entities=["ML"])]),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 1
        assert set(clusters[0]["claim_ids"]) == {"c1", "c2", "c3"}

    def test_disjoint_entities_produce_separate_clusters(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"]),
                    _claim("c2", entities=["AI"]),
                    _claim("c3", entities=["Blockchain"]),
                    _claim("c4", entities=["Blockchain"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 2
        cluster_entity_sets = [set(c["entities"]) for c in clusters]
        assert {"AI"} in cluster_entity_sets or {"Blockchain"} in cluster_entity_sets


class TestEntityLessFallback:
    def test_claims_without_entities_grouped_by_type(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", claim_type="opinion", entities=[]),
                    _claim("c2", claim_type="opinion", entities=[]),
                    _claim("c3", claim_type="prediction", entities=[]),
                    _claim("c4", claim_type="prediction", entities=[]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 2


class TestOversizedSplitting:
    def test_large_group_split_by_type(self) -> None:
        claims = [
            _claim(f"c{i}", claim_type="fact_claim" if i < 8 else "opinion", entities=["AI"])
            for i in range(15)
        ]
        items = [_item("v1", claims)]
        clusters = cluster_claims(items, max_cluster_size=12, min_cluster_size=2)
        assert len(clusters) >= 2


class TestSingletonMerging:
    def test_singleton_merged_into_nearest(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"]),
                    _claim("c2", entities=["AI"]),
                    _claim("c3", entities=["AI", "Robots"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 1
        assert "c3" in clusters[0]["claim_ids"]


class TestMinClusterSize:
    def test_single_claim_dropped_below_min_size(self) -> None:
        items = [_item("v1", [_claim("c1", entities=["Lonely"])])]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 0

    def test_high_signal_singleton_kept(self) -> None:
        items = [
            _item("v1", [_claim("c1", claim_type="market_signal", entities=["Signal"])])
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 1
        assert clusters[0]["cluster_type"] == "market_signal"


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"]),
                    _claim("c2", entities=["AI", "ML"]),
                ],
            ),
            _item("v2", [_claim("c3", entities=["ML"])]),
        ]
        r1 = cluster_claims(items)
        r2 = cluster_claims(items)
        assert r1[0]["narrative_id"] == r2[0]["narrative_id"]
        assert r1[0]["claim_ids"] == r2[0]["claim_ids"]

    def test_narrative_id_stable(self) -> None:
        items = [
            _item("v1", [_claim("c1", entities=["X"]), _claim("c2", entities=["X"])])
        ]
        clusters = cluster_claims(items)
        expected_id = derive_narrative_id(["c1", "c2"])
        assert clusters[0]["narrative_id"] == expected_id


class TestClusterFields:
    def test_cluster_has_all_required_fields(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"], confidence=0.8),
                    _claim("c2", entities=["AI"], confidence=0.6),
                ],
            ),
        ]
        clusters = cluster_claims(items)
        c = clusters[0]
        assert c["narrative_id"]
        assert c["title"]
        assert c["cluster_type"] == "theme"
        assert c["claim_count"] == 2
        assert c["source_count"] == 1
        assert 0.0 <= c["confidence"] <= 1.0
        assert 0.0 <= c["opportunity_score"] <= 1.0
        assert 0.0 <= c["risk_score"] <= 1.0
        assert isinstance(c["entities"], list)
        assert isinstance(c["keywords"], list)
        assert isinstance(c["representative_claims"], list)
        assert c["created_at"]

    def test_source_urls_populated(self) -> None:
        items = [
            _item("v1", [_claim("c1", entities=["X"]), _claim("c2", entities=["X"])]),
            _item("v2", [_claim("c3", entities=["X"])]),
        ]
        clusters = cluster_claims(items)
        assert len(clusters[0]["source_urls"]) == 2

    def test_representative_claims_top_by_confidence(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["X"], confidence=0.9, claim_text="Best claim"),
                    _claim("c2", entities=["X"], confidence=0.3, claim_text="Weak claim"),
                    _claim("c3", entities=["X"], confidence=0.5, claim_text="Mid claim"),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert clusters[0]["representative_claims"][0] == "Best claim"


class TestSafetyCapBreached:
    def test_over_500_claims_returns_empty(self) -> None:
        claims = [_claim(f"c{i}", entities=["All"]) for i in range(501)]
        items = [_item("v1", claims)]
        assert cluster_claims(items) == []


class TestInvalidClaims:
    def test_non_dict_claims_skipped(self) -> None:
        items = [{"id": "v1", "url": "u", "extracted_claims": ["bad", None, 42]}]
        assert cluster_claims(items) == []

    def test_claims_missing_claim_id_skipped(self) -> None:
        items = [
            _item(
                "v1",
                [
                    {"claim_text": "no id", "entities": ["X"]},
                    _claim("c1", entities=["X"]),
                    _claim("c2", entities=["X"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert len(clusters) == 1
        assert "c1" in clusters[0]["claim_ids"]


class TestTiedTypeVotes:
    def test_equal_type_counts_resolve_to_mixed(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", claim_type="fact_claim", entities=["X"]),
                    _claim("c2", claim_type="prediction", entities=["X"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        assert clusters[0]["cluster_type"] == "mixed"

    def test_empty_claims_resolve_to_mixed(self) -> None:
        assert _resolve_cluster_type([]) == "mixed"


class TestSingletonMergingWithEntities:
    def test_singleton_merged_by_entity_overlap(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI", "ML"]),
                    _claim("c2", entities=["AI"]),
                    _claim("c3", entities=["Blockchain", "DeFi"]),
                    _claim("c4", entities=["Blockchain"]),
                    # c5 shares no entity with any other claim → singleton
                    # but overlaps "AI" keyword in entities → merged into AI cluster
                    _claim("c5", entities=["Unique", "AI"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        ai_cluster = next(c for c in clusters if "c1" in c["claim_ids"])
        assert "c5" in ai_cluster["claim_ids"]

    def test_singleton_with_no_overlap_still_merged(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"]),
                    _claim("c2", entities=["AI"]),
                    _claim("c3", entities=["AI"]),
                    # c4 has unique entity, forms singleton, gets merged into only large group
                    _claim("c4", entities=["Quantum"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=3)
        assert len(clusters) == 1
        assert "c4" in clusters[0]["claim_ids"]

    def test_singleton_picks_best_among_multiple_large_groups(self) -> None:
        items = [
            _item(
                "v1",
                [
                    _claim("c1", entities=["AI"]),
                    _claim("c2", entities=["AI"]),
                    _claim("c3", entities=["Blockchain"]),
                    _claim("c4", entities=["Blockchain"]),
                    # c5 shares "AI" entity → should merge into AI group, not Blockchain
                    _claim("c5", entities=["Unique", "AI"]),
                ],
            ),
        ]
        clusters = cluster_claims(items, min_cluster_size=2)
        ai_cluster = next(c for c in clusters if "c1" in c["claim_ids"])
        assert "c5" in ai_cluster["claim_ids"]
