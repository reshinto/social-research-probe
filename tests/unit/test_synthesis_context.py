"""Tests for the ResearchPacket → SynthesisContext pass-through transformer."""

from __future__ import annotations

from social_research_probe.synthesize.synthesis_context import build_synthesis_context


def _scores(o=0.6, t=0.5, tr=0.4, op=0.3):
    return {"trust": t, "trend": tr, "opportunity": op, "overall": o}


def test_empty_packet_yields_empty_context():
    ctx = build_synthesis_context({})
    assert ctx["topic"] == ""
    assert ctx["platform"] == ""
    assert ctx["coverage"] == {"fetched": 0, "enriched": 0, "platforms": []}
    assert ctx["items"] == []
    assert ctx["stats_highlights"] == []
    assert ctx["chart_takeaways"] == []
    assert ctx["warnings"] == []


def test_full_packet_passthrough():
    packet = {
        "topic": "ai",
        "platform": "youtube",
        "items_top_n": [
            {
                "title": "T1",
                "url": "https://y/1",
                "scores": _scores(),
                "one_line_takeaway": "short",
                "summary": "merged summary",
                "corroboration_verdict": "supported",
            }
        ],
        "stats_summary": {
            "highlights": ["trust↔overall r=+0.71", "n=20 items"],
            "models_run": [],
            "low_confidence": False,
        },
        "chart_takeaways": ["Overall distribution: n=20"],
        "warnings": ["sparse fetch"],
    }
    ctx = build_synthesis_context(packet)
    assert ctx["topic"] == "ai"
    assert ctx["platform"] == "youtube"
    assert ctx["coverage"]["fetched"] == 20  # dug from highlights "n=20"
    assert ctx["coverage"]["enriched"] == 1
    assert ctx["coverage"]["platforms"] == ["youtube"]
    assert ctx["stats_highlights"] == ["trust↔overall r=+0.71", "n=20 items"]
    assert ctx["chart_takeaways"] == ["Overall distribution: n=20"]
    assert ctx["warnings"] == ["sparse fetch"]
    [item] = ctx["items"]
    assert item["rank"] == 1
    assert item["title"] == "T1"
    assert item["takeaway"] == "short"
    assert item["summary"] == "merged summary"
    assert item["corroboration"] == "supported"


def test_summary_falls_back_to_takeaway_when_missing():
    packet = {
        "items_top_n": [
            {"title": "T", "url": "u", "scores": _scores(), "one_line_takeaway": "only-takeaway"}
        ]
    }
    [item] = build_synthesis_context(packet)["items"]
    assert item["summary"] == "only-takeaway"


def test_corroboration_absent_when_verdict_missing():
    packet = {"items_top_n": [{"title": "T", "url": "u", "scores": _scores()}]}
    [item] = build_synthesis_context(packet)["items"]
    assert "corroboration" not in item


def test_coverage_fetched_falls_back_to_enriched_when_no_n_token():
    packet = {
        "platform": "youtube",
        "items_top_n": [{"title": "A", "url": "u"}, {"title": "B", "url": "u2"}],
        "stats_summary": {
            "highlights": ["no count token here"],
            "models_run": [],
            "low_confidence": False,
        },
    }
    ctx = build_synthesis_context(packet)
    assert ctx["coverage"]["fetched"] == 2
    assert ctx["coverage"]["enriched"] == 2
