1. `srp config check-secrets --needed-for research --platform youtube --output json`
   If `missing` is non-empty: tell user to run `srp config set-secret <name>` in a terminal (hidden prompt — never ask them to paste keys into chat). Stop until confirmed.
2. Run the research in skill mode to get the JSON packet:
   - `srp research --mode skill <topic> <purpose>` — platform defaults to `youtube`
   - `srp research --mode skill <platform> <topic> <purpose1>,<purpose2>` — multiple purposes (comma-separated)
   - Add `--no-shorts` to exclude YouTube Shorts (<90s). Shorts are included by default.
   - Note: users invoke this skill as `/srp research <topic> <purpose>` — never ask them to specify `--mode`.
3. The JSON packet contains all data. Emit sections 1–11 as follows:
   - **Sections 1–9:** Identical to `srp research --mode cli` output. Render exactly as the CLI would.
   - **Section 10 — Compiled Synthesis:** Use the template below.
   - **Section 11 — Opportunity Analysis:** Use the template below.
4. Open every chart PNG before emitting output. Extract PNG paths from `packet.chart_captions` (each caption contains a `_(see PNG: …)_` marker for scatter/table charts; bar/line PNGs live alongside under `~/.social-research-probe/charts/`). **Bar charts have no `_(see PNG: …)_` marker** — always explicitly include `~/.social-research-probe/charts/overall_score_bar.png`. On macOS run `open <path1> <path2> …`.
5. For each chart in section 8: include a clickable markdown link `[filename](full png path)` and attempt an inline preview via Claude Code's `Read` tool on the PNG path.

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
