"""Narrative clustering technology: deterministic entity-based claim grouping."""

from __future__ import annotations

from typing import ClassVar

from social_research_probe.config import load_active_config
from social_research_probe.technologies import BaseTechnology


class NarrativeClustererTech(BaseTechnology):
    """Cluster claims into narratives using entity co-occurrence and type affinity.

    Examples:
        Input:
            NarrativeClustererTech
        Output:
            NarrativeClustererTech
    """

    name: ClassVar[str] = "narrative_clusterer"
    enabled_config_key: ClassVar[str] = "narrative_clusterer"

    async def _execute(self, data: dict) -> dict:
        """Run deterministic narrative clustering on items.

        Args:
            data: Dict with 'items' key containing pipeline items with extracted_claims.

        Returns:
            Dict with 'clusters' key containing list of NarrativeCluster dicts.

        Examples:
            Input:
                await _execute(data={"items": []})
            Output:
                {"clusters": []}
        """
        from social_research_probe.utils.narratives.clusterer import cluster_claims

        items = data.get("items") or []
        if not items:
            return {"clusters": []}

        cfg = load_active_config()
        narratives_cfg = cfg.raw.get("platforms", {}).get("youtube", {}).get("narratives", {})
        min_cluster_size = int(narratives_cfg.get("min_cluster_size", 2))
        max_cluster_size = int(narratives_cfg.get("max_cluster_size", 12))

        clusters = cluster_claims(
            items,
            min_cluster_size=min_cluster_size,
            max_cluster_size=max_cluster_size,
        )
        return {"clusters": clusters}
