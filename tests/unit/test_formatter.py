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
