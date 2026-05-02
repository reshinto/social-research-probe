"""Synthetic ScoredItem builder for the offline demo report.

Returns 12 deterministic items covering all TranscriptStatus,
CommentsStatus, and EvidenceTier values, plus the four canonical
source_class values. Pure function, no I/O.
"""

from __future__ import annotations

from social_research_probe.commands._demo_constants import DEMO_THEMES
from social_research_probe.utils.core.types import (
    ScoredItem,
    SourceComment,
    TextSurrogate,
)

_DEMO_AUTHORS = (
    "viewerOne",
    "viewerTwo",
    "viewerThree",
    "viewerFour",
    "viewerFive",
    "viewerSix",
)

_DEMO_COMMENT_BANK = (
    "Switched to pair-programming with the agent and shipped twice as fast.",
    "Junior hires on my team now spend most of their week reviewing AI output.",
    "Bootcamp grads are showing up without code-review fundamentals.",
    "Agent reliability falls off a cliff above 200 lines of context.",
    "We retired three internal tools after wiring up an agent runner.",
    "Our staff engineers became force multipliers once code review went async.",
)


def _theme(idx: int) -> str:
    return DEMO_THEMES[idx % len(DEMO_THEMES)]


def _scores(trust: float, trend: float, opportunity: float) -> dict:
    overall = round((trust + trend + opportunity) / 3, 2)
    return {
        "trust": trust,
        "trend": trend,
        "opportunity": opportunity,
        "overall": overall,
    }


def _features(view_velocity: float, engagement: float, age: float, subs: float) -> dict:
    return {
        "view_velocity": view_velocity,
        "engagement_ratio": engagement,
        "age_days": age,
        "subscriber_count": subs,
    }


def _comments_for(idx: int, count: int) -> list[str]:
    if count == 0:
        return []
    return [_DEMO_COMMENT_BANK[(idx + n) % len(_DEMO_COMMENT_BANK)] for n in range(count)]


def _source_comments_for(idx: int, source_id: str, count: int) -> list[SourceComment]:
    if count == 0:
        return []
    out: list[SourceComment] = []
    for n in range(count):
        author_idx = (idx + n) % len(_DEMO_AUTHORS)
        out.append(
            {
                "source_id": source_id,
                "platform": "youtube",
                "comment_id": f"{source_id}-c{n + 1}",
                "author": _DEMO_AUTHORS[author_idx],
                "text": _DEMO_COMMENT_BANK[(idx + n) % len(_DEMO_COMMENT_BANK)],
                "like_count": 12 + (idx * 7 + n * 3) % 88,
                "published_at": f"2026-04-{(idx + n) % 28 + 1:02d}T12:00:00Z",
            }
        )
    return out


def _text_surrogate(
    source_id: str,
    title: str,
    description: str,
    transcript: str,
    transcript_status: str,
    evidence_tier: str,
    comments: list[str],
    layers: list[str],
) -> TextSurrogate:
    primary_text = transcript or description or title
    primary_text_source = (
        "transcript"
        if transcript
        else ("description" if description else "title")
    )
    return {
        "source_id": source_id,
        "platform": "youtube",
        "url": f"https://www.youtube.com/watch?v={source_id}",
        "title": title,
        "description": description,
        "channel_or_author": "Demo Channel",
        "published_at": "2026-04-15T12:00:00Z",
        "comments": list(comments),
        "transcript": transcript,
        "transcript_status": transcript_status,  # type: ignore[typeddict-item]
        "external_snippets": [],
        "primary_text": primary_text,
        "primary_text_source": primary_text_source,
        "evidence_layers": list(layers),
        "evidence_tier": evidence_tier,  # type: ignore[typeddict-item]
        "confidence_penalties": [],
        "warnings": [],
        "char_count": len(primary_text),
    }


def _build_item(
    idx: int,
    source_id: str,
    title: str,
    channel: str,
    source_class: str,
    transcript_status: str,
    comments_status: str,
    evidence_tier: str,
    verdict: str,
    comment_count: int,
    trust: float,
    trend: float,
    opportunity: float,
    transcript_text: str = "",
    layers: list[str] | None = None,
) -> ScoredItem:
    description = f"Channel deep-dive on {_theme(idx)}; covers concrete examples."
    summary = (
        f"Item {idx + 1} explores {_theme(idx)} with concrete examples drawn "
        "from contemporary engineering practice."
    )
    one_line = f"Signal on {_theme(idx)} for engineering decisions."
    comments = _comments_for(idx, comment_count)
    source_comments = _source_comments_for(idx, source_id, comment_count)
    surrogate = _text_surrogate(
        source_id=source_id,
        title=title,
        description=description,
        transcript=transcript_text,
        transcript_status=transcript_status,
        evidence_tier=evidence_tier,
        comments=comments,
        layers=layers or [],
    )
    item: ScoredItem = {
        "title": title,
        "channel": channel,
        "url": f"https://www.youtube.com/watch?v={source_id}",
        "source_class": source_class,
        "scores": _scores(trust, trend, opportunity),  # type: ignore[typeddict-item]
        "features": _features(  # type: ignore[typeddict-item]
            view_velocity=120.0 + idx * 15.0,
            engagement=0.04 + idx * 0.005,
            age=7.0 + idx * 2.0,
            subs=10000.0 + idx * 1500.0,
        ),
        "one_line_takeaway": one_line,
        "summary": summary,
        "summary_source": "transcript" if transcript_text else "description",
        "transcript": transcript_text,
        "transcript_status": transcript_status,  # type: ignore[typeddict-item]
        "evidence_tier": evidence_tier,  # type: ignore[typeddict-item]
        "text_surrogate": surrogate,
        "corroboration_verdict": verdict,
        "comments_status": comments_status,  # type: ignore[typeddict-item]
        "source_comments": source_comments,
        "comments": comments,
    }
    return item


_DEMO_ITEM_SPECS: tuple[dict, ...] = (
    {
        "source_id": "demo001",
        "title": "Junior Devs and the AI Coding Agent Shift",
        "channel": "Field Notes from Engineering",
        "source_class": "primary",
        "transcript_status": "available",
        "comments_status": "available",
        "evidence_tier": "metadata_comments_transcript",
        "verdict": "verified",
        "comment_count": 6,
        "trust": 0.88,
        "trend": 0.82,
        "opportunity": 0.74,
        "transcript_text": (
            "Engineering managers report that junior roles are compressing as "
            "AI coding agents absorb routine implementation work."
        ),
        "layers": ["title", "description", "transcript", "comments"],
    },
    {
        "source_id": "demo002",
        "title": "Pair Programming Premium in the Agent Era",
        "channel": "Staff Eng Diaries",
        "source_class": "primary",
        "transcript_status": "available",
        "comments_status": "available",
        "evidence_tier": "full",
        "verdict": "verified",
        "comment_count": 5,
        "trust": 0.92,
        "trend": 0.78,
        "opportunity": 0.81,
        "transcript_text": (
            "Senior engineers describe pair-programming with agents as the "
            "highest-leverage activity of their week."
        ),
        "layers": [
            "title",
            "description",
            "transcript",
            "comments",
            "external_corroboration",
        ],
    },
    {
        "source_id": "demo003",
        "title": "Code Review as the New Senior Signal",
        "channel": "Engineering Leadership Lab",
        "source_class": "primary",
        "transcript_status": "available",
        "comments_status": "unavailable",
        "evidence_tier": "metadata_transcript",
        "verdict": "partially_verified",
        "comment_count": 0,
        "trust": 0.74,
        "trend": 0.66,
        "opportunity": 0.62,
        "transcript_text": (
            "Hiring panels increasingly evaluate code-review competence as "
            "the differentiator between mid-level and senior candidates."
        ),
        "layers": ["title", "description", "transcript"],
    },
    {
        "source_id": "demo004",
        "title": "AI Agent Reliability: The 200-Line Cliff",
        "channel": "Tools and Tradeoffs",
        "source_class": "secondary",
        "transcript_status": "unavailable",
        "comments_status": "available",
        "evidence_tier": "metadata_comments",
        "verdict": "unverified",
        "comment_count": 4,
        "trust": 0.42,
        "trend": 0.55,
        "opportunity": 0.48,
        "transcript_text": "",
        "layers": ["title", "description", "comments"],
    },
    {
        "source_id": "demo005",
        "title": "Bootcamp Curriculum Churn 2026",
        "channel": "Career Pivot Weekly",
        "source_class": "secondary",
        "transcript_status": "failed",
        "comments_status": "failed",
        "evidence_tier": "metadata_only",
        "verdict": "unverified",
        "comment_count": 0,
        "trust": 0.28,
        "trend": 0.45,
        "opportunity": 0.32,
        "transcript_text": "",
        "layers": ["title", "description"],
    },
    {
        "source_id": "demo006",
        "title": "Why Some Channels Block Transcript Fetchers",
        "channel": "Open Web Notes",
        "source_class": "secondary",
        "transcript_status": "provider_blocked",
        "comments_status": "available",
        "evidence_tier": "metadata_comments",
        "verdict": "partially_verified",
        "comment_count": 3,
        "trust": 0.38,
        "trend": 0.41,
        "opportunity": 0.36,
        "transcript_text": "",
        "layers": ["title", "description", "comments"],
    },
    {
        "source_id": "demo007",
        "title": "Late-Night Take: Are Junior Devs Cooked?",
        "channel": "Hot Takes Daily",
        "source_class": "commentary",
        "transcript_status": "timeout",
        "comments_status": "disabled",
        "evidence_tier": "metadata_only",
        "verdict": "unverified",
        "comment_count": 0,
        "trust": 0.18,
        "trend": 0.62,
        "opportunity": 0.21,
        "transcript_text": "",
        "layers": ["title", "description"],
    },
    {
        "source_id": "demo008",
        "title": "Opinion Piece: The Coming Junior Dev Shortage",
        "channel": "Industry Editorials",
        "source_class": "commentary",
        "transcript_status": "disabled",
        "comments_status": "not_attempted",
        "evidence_tier": "metadata_only",
        "verdict": "unverified",
        "comment_count": 0,
        "trust": 0.21,
        "trend": 0.51,
        "opportunity": 0.27,
        "transcript_text": "",
        "layers": ["title", "description"],
    },
    {
        "source_id": "demo009",
        "title": "Listener Mailbag: Should I Still Learn to Code?",
        "channel": "Career Q&A Cast",
        "source_class": "commentary",
        "transcript_status": "not_attempted",
        "comments_status": "available",
        "evidence_tier": "metadata_comments",
        "verdict": "unverified",
        "comment_count": 4,
        "trust": 0.32,
        "trend": 0.48,
        "opportunity": 0.44,
        "transcript_text": "",
        "layers": ["title", "description", "comments"],
    },
    {
        "source_id": "demo010",
        "title": "Cross-Industry Roundup: AI in the SDLC",
        "channel": "Practitioner Podcast",
        "source_class": "unknown",
        "transcript_status": "available",
        "comments_status": "available",
        "evidence_tier": "metadata_external",
        "verdict": "partially_verified",
        "comment_count": 5,
        "trust": 0.58,
        "trend": 0.69,
        "opportunity": 0.65,
        "transcript_text": (
            "Cross-industry data suggests AI agents are reshaping the entire "
            "software development lifecycle, not only individual coding tasks."
        ),
        "layers": ["title", "description", "transcript", "external_corroboration"],
    },
    {
        "source_id": "demo011",
        "title": "Pairing With Agents: A Field Study",
        "channel": "Field Notes from Engineering",
        "source_class": "primary",
        "transcript_status": "available",
        "comments_status": "available",
        "evidence_tier": "metadata_comments_transcript",
        "verdict": "verified",
        "comment_count": 5,
        "trust": 0.85,
        "trend": 0.71,
        "opportunity": 0.78,
        "transcript_text": (
            "Field study of 40 engineering teams quantifies pair-programming "
            "skill premium and code-review hours per ship."
        ),
        "layers": ["title", "description", "transcript", "comments"],
    },
    {
        "source_id": "demo012",
        "title": "Hiring Funnel Telemetry After Agent Adoption",
        "channel": "Hiring Signal",
        "source_class": "secondary",
        "transcript_status": "available",
        "comments_status": "available",
        "evidence_tier": "full",
        "verdict": "verified",
        "comment_count": 4,
        "trust": 0.81,
        "trend": 0.76,
        "opportunity": 0.95,
        "transcript_text": (
            "Aggregated ATS telemetry shows junior funnel volume down 38% YoY "
            "while senior code-review screens are the new gate."
        ),
        "layers": [
            "title",
            "description",
            "transcript",
            "comments",
            "external_corroboration",
        ],
    },
)


def build_demo_items() -> list[ScoredItem]:
    """Return 12 deterministic synthetic ScoredItem dicts."""
    return [_build_item(idx, **spec) for idx, spec in enumerate(_DEMO_ITEM_SPECS)]
