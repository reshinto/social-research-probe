# Synthesis Authoring

[Home](README.md) → Synthesis Authoring

The HTML report includes deterministic packet sections plus three synthesis sections: Compiled Synthesis, Opportunity Analysis, and Final Summary. Those synthesis sections are written by an LLM runner when one is configured, or left as placeholders when `llm.runner = none`.

In the Claude Code skill, the host model can still draft those synthesis sections when `llm.runner = none`; `srp report` is how you inject that text back into the HTML report.

You can **override** those synthesis sections after the fact by passing plain-text files to `srp report`. This guide covers:

1. When you would override (and when you would not).
2. How to invoke `srp report` with custom synthesis.
3. Author templates for each section.

---

## When to override

- The default LLM output missed a key finding you want to emphasise.
- You ran research with `llm.runner = none` and now want to add synthesis by hand.
- You used the Claude Code skill to draft the synthesis sections with the host model and want that text written into the HTML report.
- You want to use a different runner (e.g. Claude in a separate session) to author the synthesis sections, then inject them.

When **not** to override: if the default synthesis is acceptable, ship it. Re-running `srp report` only changes Compiled Synthesis, Opportunity Analysis, and Final Summary — the charts, stats, and top-N come from the packet.

---

## How to invoke

```bash
# 1. Write the synthesis sections to plain-text files
printf "%s\n" "- **What was searched:** …" > /tmp/compiled-synthesis.txt
printf "%s\n" "- **Best content gap:** …" > /tmp/opportunity-analysis.txt
printf "%s\n" "- **Executive summary:** …" > /tmp/final-summary.txt

# 2. Re-render the report, pointing at the original packet JSON
srp report \
  --packet ~/.social-research-probe/reports/<packet>.json \
  --compiled-synthesis /tmp/compiled-synthesis.txt \
  --opportunity-analysis /tmp/opportunity-analysis.txt \
  --final-summary /tmp/final-summary.txt \
  --out ~/.social-research-probe/reports/<packet>.html
```

`srp report` intentionally bypasses the LLM runner — it is the post-hoc synthesis path.

---

## Compiled Synthesis template

Write in plain English. No statistics jargon. Bullet points only. Target audience: someone who has never seen a stats report.

- **What was searched:** One sentence — topic, platform, how many videos looked at.
- **What's popular right now:** 2–3 bullets on what types of content are getting the most views, in plain words.
- **Quality of results:** 1 bullet — are the results trustworthy sources or clickbait? How spread out are the scores?
- **How fast things move:** 1 bullet — how quickly do videos gain views, and how long do they stay popular?
- **One surprising finding:** 1 bullet — the most unexpected or interesting thing the data showed.

---

## Opportunity Analysis template

Write in plain English. Actionable bullets only. Each bullet should answer "what should someone DO with this information?"

- **Best content gap:** What type of content is missing that people are clearly looking for?
- **Best timing:** When should someone publish to get the most views?
- **Best audience to target:** Which audience size/type is most engaged right now?
- **One thing to avoid:** What approach is clearly not working based on the data?
- **Quick win:** The single easiest action someone could take today based on these findings.

---

## Related

- [Usage](usage.md) — end-to-end `srp research` workflow
- [Charts](charts.md) — what each chart in the report shows
- [LLM Runners](llm-runners.md) — enable a runner to get the synthesis sections generated automatically
