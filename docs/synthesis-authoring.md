# Synthesis Authoring — Sections 10 & 11

[Home](README.md) → Synthesis Authoring

The HTML report includes 11 sections. Sections 1–9 are generated mechanically from the research packet. Sections 10 (Compiled Synthesis) and 11 (Opportunity Analysis) are written by an LLM runner when one is configured, or left as placeholders when `llm.runner = none`.

You can **override** sections 10–11 after the fact by passing plain-text files to `srp report`. This guide covers:

1. When you would override (and when you would not).
2. How to invoke `srp report` with custom synthesis.
3. Author templates for each section.

---

## When to override

- The default LLM output missed a key finding you want to emphasise.
- You ran research with `llm.runner = none` and now want to add synthesis by hand.
- You want to use a different runner (e.g. Claude in a separate session) to author the sections, then inject them.

When **not** to override: if the default synthesis is acceptable, ship it. Re-running `srp report` only changes sections 10–11 — the charts, stats, and top-5 come from the packet.

---

## How to invoke

```bash
# 1. Write the two sections to plain-text files
printf "%s\n" "- **What was searched:** …" > /tmp/s10.txt
printf "%s\n" "- **Best content gap:** …"    > /tmp/s11.txt

# 2. Re-render the report, pointing at the original packet JSON
srp report \
  --packet ~/.social-research-probe/reports/<packet>.json \
  --synthesis-10 /tmp/s10.txt \
  --synthesis-11 /tmp/s11.txt \
  --out ~/.social-research-probe/reports/<packet>.html
```

`srp report` intentionally bypasses the LLM runner — it is the post-hoc synthesis path.

---

## Section 10 — Compiled Synthesis template

Write in plain English. No statistics jargon. Bullet points only. Target audience: someone who has never seen a stats report.

- **What was searched:** One sentence — topic, platform, how many videos looked at.
- **What's popular right now:** 2–3 bullets on what types of content are getting the most views, in plain words.
- **Quality of results:** 1 bullet — are the results trustworthy sources or clickbait? How spread out are the scores?
- **How fast things move:** 1 bullet — how quickly do videos gain views, and how long do they stay popular?
- **One surprising finding:** 1 bullet — the most unexpected or interesting thing the data showed.

---

## Section 11 — Opportunity Analysis template

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
- [LLM Runners](llm-runners.md) — enable a runner to get sections 10–11 generated automatically
