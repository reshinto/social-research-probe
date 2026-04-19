from __future__ import annotations

from enum import StrEnum

from social_research_probe.platforms.base import RawItem, TrustHints

_PRIMARY_DOMAINS = ("arxiv.org", "nature.com", "ieee.org", "acm.org",
                    ".gov", ".edu", "who.int", "nih.gov")

class SourceClass(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    COMMENTARY = "commentary"
    UNKNOWN = "unknown"

def _has_primary_citation(markers: list[str]) -> bool:
    return any(any(d in m.lower() for d in _PRIMARY_DOMAINS) for m in markers)

def classify(item: RawItem, hints: TrustHints) -> SourceClass:
    markers = hints.citation_markers or []
    age = hints.account_age_days or 0
    subs = hints.subscriber_count or 0
    verified = bool(hints.verified)

    if verified and age >= 365 and (_has_primary_citation(markers) or subs >= 100_000):
        return SourceClass.PRIMARY
    if not markers and age < 180 and subs < 5_000:
        return SourceClass.COMMENTARY
    if markers or subs >= 1_000:
        return SourceClass.SECONDARY
    return SourceClass.UNKNOWN
