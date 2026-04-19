# Output Format — run-research

Read this file before emitting any output. Follow every section exactly as written.
Substitute `{{placeholders}}` with real values from the JSON packet.
Sections with lists expand per item; empty lists use the fallback shown.

---

## 1. Topic & Purpose

- **Topic:** {{packet.topic}}
- **Purposes:** {{packet.purpose_set joined with ", "}}

## 2. Platform

- **Platform:** {{packet.platform}}

## 3. Top Items

Render the score table first, then the links-and-takeaways list. Both are mandatory.

**Score table** (one row per item in `packet.items_top5`):

| # | Channel | Class | Trust | Trend | Opp | Overall | Title |
|---|---------|-------|-------|-------|-----|---------|-------|
| {{rank}} | {{channel}} | {{source_class}} | {{trust 2dp}} | {{trend 2dp}} | {{opportunity 2dp}} | {{overall 2dp}} | {{title}} |

**Links & takeaways** (one bullet per item — URL and one_line_takeaway are mandatory):

- **[{{rank}}]** [{{channel}}]({{url}}) — {{one_line_takeaway}}

Fallback if items_top5 is empty: `_(no items returned)_`

## 4. Platform Signals

Split `packet.platform_signals_summary` on `;` and render each part as a bullet:

- {{part}}

## 5. Source Validation

- validated: {{svs.validated}}, partial: {{svs.partially}}, unverified: {{svs.unverified}}, low-trust: {{svs.low_trust}}
- primary/secondary/commentary: {{svs.primary}}/{{svs.secondary}}/{{svs.commentary}}
- notes: {{svs.notes}}  ← omit this line if svs.notes is empty

## 6. Evidence

Split `packet.evidence_summary` on `;` and render each part as a bullet:

- {{part}}

## 7. Statistics

**Models:** {{packet.stats_summary.models_run joined with ", "}}{{" (low confidence)" if low_confidence else ""}}

{{each highlight from packet.stats_summary.highlights as "- {{highlight}}"}}

Fallback if no highlights: `_(no highlights)_`

## 8. Charts

Render every chart in this fixed order. For each chart: show the caption text, then inline the PNG with Claude Code's `Read` tool on the PNG path (for terminals that support it).

**Mandatory order:**
1. `~/.social-research-probe/charts/overall_score_bar.png` — always first; bar charts have no `_(see PNG: …)_` marker so this path must be constructed explicitly
2. All remaining charts from `packet.chart_captions` in the order they appear — extract the PNG path from each `_(see PNG: …)_` marker; for bar/line chart captions without a marker, construct the path from the chart title

For each chart entry, format as:

**{{chart title or caption heading}}**

{{ascii chart body if present}}

[{{filename}}]({{full png path}})  ← always include as a clickable link
{{inline Read tool call on the PNG path}}

Fallback if chart_captions is empty: `_(no charts rendered)_`

## 9. Warnings

{{each warning from packet.warnings as "- {{warning}}"}}

Fallback if warnings is empty: `_(none)_`

## 10. Compiled Synthesis

{{compiled_synthesis — ≤150 words, evidence-grounded summary}}

## 11. Opportunity Analysis

{{opportunity_analysis — ≤150 words, actionable opportunities}}
