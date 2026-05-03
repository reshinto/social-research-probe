"""Synthetic ScoredItem builder for the offline demo report.

Returns 12 deterministic items covering all TranscriptStatus,
CommentsStatus, and EvidenceTier values, plus the four canonical
source_class values. Pure function, no I/O.
"""

from __future__ import annotations

from social_research_probe.utils.core.types import (
    ExtractedClaim,
    ScoredItem,
    SourceComment,
    TextSurrogate,
)
from social_research_probe.utils.demo.constants import DEMO_THEMES

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
    """Document the theme rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        idx: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _theme(
                idx=3,
            )
        Output:
            "AI safety"
    """
    return DEMO_THEMES[idx % len(DEMO_THEMES)]


def _scores(trust: float, trend: float, opportunity: float) -> dict:
    """Document the scores rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        trust: Numeric score, threshold, prior, or confidence value.
        trend: Numeric score, threshold, prior, or confidence value.
        opportunity: Numeric score, threshold, prior, or confidence value.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _scores(
                trust=0.75,
                trend=0.75,
                opportunity=0.75,
            )
        Output:
            {"enabled": True}
    """
    overall = round((trust + trend + opportunity) / 3, 2)
    return {
        "trust": trust,
        "trend": trend,
        "opportunity": opportunity,
        "overall": overall,
    }


def _features(view_velocity: float, engagement: float, age: float, subs: float) -> dict:
    """Document the features rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        view_velocity: Numeric score, threshold, prior, or confidence value.
        engagement: Numeric score, threshold, prior, or confidence value.
        age: Numeric score, threshold, prior, or confidence value.
        subs: Numeric score, threshold, prior, or confidence value.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _features(
                view_velocity=0.75,
                engagement=0.75,
                age=0.75,
                subs=0.75,
            )
        Output:
            {"enabled": True}
    """
    return {
        "view_velocity": view_velocity,
        "engagement_ratio": engagement,
        "age_days": age,
        "subscriber_count": subs,
    }


def _comments_for(idx: int, count: int) -> list[str]:
    """Document the comments for rule at the boundary where callers use it.

    Downstream stages can read the same fields regardless of which source text was available.

    Args:
        idx: Count, database id, index, or limit that bounds the work being performed.
        count: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _comments_for(
                idx=3,
                count=3,
            )
        Output:
            ["AI safety", "model evaluation"]
    """
    if count == 0:
        return []
    return [_DEMO_COMMENT_BANK[(idx + n) % len(_DEMO_COMMENT_BANK)] for n in range(count)]


def _source_comments_for(idx: int, source_id: str, count: int) -> list[SourceComment]:
    """Document the source comments for rule at the boundary where callers use it.

    Later stages should not care whether comments were fetched, unavailable, or skipped; they just
    read the same fields.

    Args:
        idx: Count, database id, index, or limit that bounds the work being performed.
        source_id: Stable source identifier or URL used to join records across stages and exports.
        count: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _source_comments_for(
                idx=3,
                source_id="youtube:abc123",
                count=3,
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
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
    """Document the text surrogate rule at the boundary where callers use it.

    The report pipeline needs a predictable text payload even when transcripts or summaries are
    missing.

    Args:
        source_id: Stable source identifier or URL used to join records across stages and exports.
        title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        description: Source text, prompt text, or raw value being parsed, normalized, classified, or
                     sent to a provider.
        transcript: Source text, prompt text, or raw value being parsed, normalized, classified, or
                    sent to a provider.
        transcript_status: Lifecycle, evidence, or provider status being written into the output
                           record.
        evidence_tier: Evidence provenance label written with extracted claims.
        comments: Comment records or text used as audience evidence.
        layers: Evidence-layer records that describe which source text was available.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _text_surrogate(
                source_id="youtube:abc123",
                title="This tool reduces latency by 30%.",
                description="This tool reduces latency by 30%.",
                transcript="This tool reduces latency by 30%.",
                transcript_status="available",
                evidence_tier="direct",
                comments=[{"text": "Useful point"}],
                layers=[{"kind": "transcript", "available": True}],
            )
        Output:
            "AI safety"
    """
    primary_text = transcript or description or title
    primary_text_source = (
        "transcript" if transcript else ("description" if description else "title")
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
    """Build build item in the shape consumed by the next project step.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        idx: Count, database id, index, or limit that bounds the work being performed.
        source_id: Stable source identifier or URL used to join records across stages and exports.
        title: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        channel: YouTube channel name, id, or classification map used for source labeling.
        source_class: Source-class label such as primary, secondary, commentary, or unknown.
        transcript_status: Lifecycle, evidence, or provider status being written into the output
                           record.
        comments_status: Lifecycle, evidence, or provider status being written into the output
                         record.
        evidence_tier: Evidence provenance label written with extracted claims.
        verdict: Lifecycle, evidence, or provider status being written into the output record.
        comment_count: Count, database id, index, or limit that bounds the work being performed.
        trust: Numeric score, threshold, prior, or confidence value.
        trend: Numeric score, threshold, prior, or confidence value.
        opportunity: Numeric score, threshold, prior, or confidence value.
        transcript_text: Source text, prompt text, or raw value being parsed, normalized,
                         classified, or sent to a provider.
        layers: Evidence-layer records that describe which source text was available.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _build_item(
                idx=3,
                source_id="youtube:abc123",
                title="This tool reduces latency by 30%.",
                channel="OpenAI",
                source_class="primary",
                transcript_status="available",
                comments_status="available",
                evidence_tier="direct",
                verdict="supported",
                comment_count=3,
                trust=0.75,
                trend=0.75,
                opportunity=0.75,
                transcript_text="This tool reduces latency by 30%.",
                layers=[{"kind": "transcript", "available": True}],
            )
        Output:
            "AI safety"
    """
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
            "AI coding agents absorb routine implementation work. "
            "AI coding agents will automate an estimated 50% of routine implementation tasks. "
            "However, some managers report higher error rates when agents work unsupervised."
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
            "highest-leverage activity of their week. "
            "Recommend adopting agent-assisted pair-programming as the baseline for all "
            "engineering teams. "
            "In my experience, pair-programming with agents cuts implementation time by at "
            "least 40%."
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
            "the differentiator between mid-level and senior candidates. "
            "I believe code review is now the most critical skill for any senior engineer. "
            "Many junior developers struggle to keep up with the volume of AI-generated code."
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
            "software development lifecycle, not only individual coding tasks. "
            "Adoption of agent-assisted workflows is growing rapidly across the industry. "
            "Should developers prioritize learning to work alongside AI agents?"
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


def _extract_item_claims(item: ScoredItem) -> list[ExtractedClaim]:
    """Extract item claims from the supplied content.

    Extraction, review, corroboration, and reporting all need the same claim shape.

    Args:
        item: Single source item, database row, or registry entry being transformed.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _extract_item_claims(
                item={"title": "Example", "url": "https://youtu.be/demo"},
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    from social_research_probe.utils.claims.extractor import extract_claims_deterministic

    surrogate: TextSurrogate = item.get("text_surrogate") or {}
    text: str = surrogate.get("primary_text") or ""
    return extract_claims_deterministic(
        text=text,
        source_id=surrogate.get("source_id") or "",
        source_url=item.get("url") or "",
        source_title=item.get("title") or "",
        evidence_layer=surrogate.get("primary_text_source") or "title",
        evidence_tier=surrogate.get("evidence_tier") or "metadata_only",
    )


def build_demo_items() -> list[ScoredItem]:
    """Return 12 deterministic synthetic ScoredItem dicts.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            build_demo_items()
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    items = [_build_item(idx, **spec) for idx, spec in enumerate(_DEMO_ITEM_SPECS)]
    for item in items:
        item["extracted_claims"] = _extract_item_claims(item)
    return items
