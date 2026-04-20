"""Concurrent corroboration of top-5 items via configured search backends."""

from __future__ import annotations

import asyncio

from social_research_probe.types import ScoredItem
from social_research_probe.utils.progress import log


async def _corroborate_one(
    item: ScoredItem,
    backends: list[str],
    sem: asyncio.Semaphore,
) -> dict:
    """Corroborate a single item using its title as the claim text.

    Runs inside an asyncio event loop created per worker thread so nested
    ``asyncio.run`` calls in ``corroborate_claim`` work safely.
    """
    from social_research_probe.corroboration.host import corroborate_claim
    from social_research_probe.validation.claims import Claim

    claim = Claim(
        text=item.get("title", ""),
        source_text=item.get("one_line_takeaway") or item.get("title", ""),
        index=0,
    )
    async with sem:
        return await corroborate_claim(claim, backends)


async def _corroborate_top5(top5: list[ScoredItem], backends: list[str]) -> list[dict]:
    """Corroborate all top-5 items concurrently, one claim per item.

    Uses the video title as the claim text — short, factual, and searchable.
    The AI-generated one_line_takeaway is passed as source context. Caps
    concurrent API calls to 3 to respect search-backend rate limits.
    """
    log(f"[srp] corroboration: starting — {len(top5)} items to check via {', '.join(backends)}")

    async def _gather() -> list[dict]:
        sem = asyncio.Semaphore(3)
        results = await asyncio.gather(
            *[_corroborate_one(item, backends, sem) for item in top5],
            return_exceptions=True,
        )
        return [r if isinstance(r, dict) else {} for r in results]

    results = await _gather()
    verdicts = [r.get("aggregate_verdict", "no_result") for r in results]
    summary = ", ".join(
        f"{v}={verdicts.count(v)}"
        for v in ("supported", "inconclusive", "refuted", "no_result")
        if verdicts.count(v)
    )
    log(f"[srp] corroboration: done — {summary}")
    return results
