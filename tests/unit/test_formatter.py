from social_research_probe.synthesize.formatter import build_packet, render_sections_1_9

def test_build_packet_shape():
    items = [{"title":"A","channel":"C","url":"u","source_class":"primary",
              "scores":{"trust":0.9,"trend":0.5,"opportunity":0.4,"overall":0.7},
              "one_line_takeaway":"x"}]
    pkt = build_packet(
        topic="ai agents", platform="youtube",
        purpose_set=["trends"], items_top5=items,
        source_validation_summary={"validated":1,"partially":0,"unverified":0,
                                   "low_trust":0,"primary":1,"secondary":0,
                                   "commentary":0,"notes":""},
        platform_signals_summary="ok",
        evidence_summary="ok",
        stats_summary={"models_run":["descriptive"],"highlights":[],"low_confidence":False},
        chart_captions=[], warnings=[],
    )
    assert pkt["topic"] == "ai agents"
    assert pkt["response_schema"]["compiled_synthesis"].startswith("string")

def test_render_sections_contains_headings():
    out = render_sections_1_9({"topic":"ai","platform":"youtube",
        "purpose_set":["trends"],"items_top5":[],
        "source_validation_summary":{"validated":0,"partially":0,"unverified":0,
            "low_trust":0,"primary":0,"secondary":0,"commentary":0,"notes":""},
        "platform_signals_summary":"-","evidence_summary":"-",
        "stats_summary":{"models_run":[],"highlights":[],"low_confidence":False},
        "chart_captions":[],"warnings":[]})
    for h in ("## 1.", "## 2.", "## 9."):
        assert h in out


def test_render_sections_with_items():
    """Cover _fmt_item (lines 27-28) and the non-empty items branch (line 44)."""
    from social_research_probe.synthesize.formatter import render_sections_1_9, _fmt_item
    item = {
        "title": "Test Video",
        "channel": "Test Channel",
        "url": "https://example.com",
        "source_class": "primary",
        "scores": {"trust": 0.8, "trend": 0.6, "opportunity": 0.5, "overall": 0.7},
        "one_line_takeaway": "A great takeaway.",
    }
    # Direct call to _fmt_item
    line = _fmt_item(1, item)
    assert "Test Video" in line
    assert "trust=0.80" in line

    # render_sections_1_9 with items triggers line 44
    out = render_sections_1_9({
        "topic": "ai", "platform": "youtube",
        "purpose_set": ["trends"], "items_top5": [item],
        "source_validation_summary": {
            "validated": 0, "partially": 0, "unverified": 1,
            "low_trust": 0, "primary": 1, "secondary": 0, "commentary": 0, "notes": "",
        },
        "platform_signals_summary": "5 items fetched",
        "evidence_summary": "live fetch",
        "stats_summary": {"models_run": [], "highlights": [], "low_confidence": False},
        "chart_captions": [], "warnings": [],
    })
    assert "## 3. Top Items" in out
    assert "Test Video" in out
