"""Demo narrative clusters built from demo items using the real clustering algorithm."""

from __future__ import annotations


def build_demo_narratives(items: list[dict]) -> list[dict]:
    """Cluster demo items into narratives using the real deterministic algorithm.

    Args:
        items: Demo items with extracted_claims fields.

    Returns:
        List of NarrativeCluster dicts.
    """
    from social_research_probe.utils.narratives.clusterer import cluster_claims

    return cluster_claims(items)
