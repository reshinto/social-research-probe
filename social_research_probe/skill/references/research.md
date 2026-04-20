1. `srp config check-secrets --needed-for research --platform youtube --output json`
   If `missing` is non-empty: tell user to run `srp config set-secret <name>` in a terminal (hidden prompt — never ask them to paste keys into chat). Stop until confirmed.
2. Run the research to get the JSON packet:
   - `srp research <topic> <purpose>` — platform defaults to `youtube`
   - `srp research <platform> <topic> <purpose1>,<purpose2>` — multiple purposes (comma-separated)
   - `srp research [<platform>] "<natural language query>"` — single free-form sentence; the CLI auto-classifies it into a topic and purpose (using the configured LLM runner), persists any new topic/purpose to the taxonomy, then runs research. Requires `llm.runner != none`.
   - Add `--no-shorts` to exclude YouTube Shorts (<90s). Shorts are included by default.
   - Note: users invoke this skill as `/srp research <topic> <purpose>`.
3. **HTML report is written automatically.** The CLI prints the report path to stderr as `[srp] HTML report: file:///...`. Surface that path to the user immediately:
   - Tell the user: `Open your report: file:///~/.social-research-probe/reports/<filename>.html`
   - The HTML is self-contained and opens in any browser. It includes all 11 sections, embedded charts, and a built-in text-to-speech player.
   - If the LLM runner is configured (`llm.runner != none`), sections 10–11 are already written into the HTML. If not, they show a placeholder.
4. If the user wants to supply custom sections 10–11 after the fact, use `srp report`:
   - Write section 10 to a temp file: e.g. `/tmp/s10.txt`
   - Write section 11 to a temp file: e.g. `/tmp/s11.txt`
   - Run: `srp report --packet <packet-json-path> --synthesis-10 /tmp/s10.txt --synthesis-11 /tmp/s11.txt --out <html-path>`
5. Emit a brief Markdown summary of sections 1–9 in the chat (so the user can read key findings inline). Do **not** re-emit the full report — the HTML file is the authoritative document.
   - **Section 3 — Top Items links & takeaways:** for each item, if `packet.items_top5[i].transcript` is present, write a 1–2 sentence summary of the video. Do not quote verbatim. Fall back to `one_line_takeaway` if no transcript.
   - **Section 10 and 11:** omit from inline output if the HTML already contains them (runner was configured). If placeholders are present, render the sections using the templates below.
6. Open every chart PNG (macOS: `open <paths…>`). PNG paths are in `packet.chart_captions` via `_(see PNG: …)_` markers. Bar chart has no marker — use `~/.social-research-probe/charts/overall_score_bar.png`.

---

## Section 10 — Compiled Synthesis template

Write in plain English. No statistics jargon. Bullet points only. Target: someone who has never seen a stats report.

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
