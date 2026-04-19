1. `srp config check-secrets --needed-for research --platform youtube --output json`
   If `missing` is non-empty: tell user to run `srp config set-secret <name>` in a terminal (hidden prompt — never ask them to paste keys into chat). Stop until confirmed.
2. Run the research in skill mode to get the JSON packet:
   - `srp research --mode skill <topic> <purpose>` — platform defaults to `youtube`
   - `srp research --mode skill <platform> <topic> <purpose1>,<purpose2>` — multiple purposes (comma-separated)
   - Add `--no-shorts` to exclude YouTube Shorts (<90s). Shorts are included by default.
3. The JSON packet contains all data. Emit sections 1–11 as follows:
   - **Sections 1–9:** The structure is identical to `srp research --mode cli` output. Render them exactly as the CLI would — same section headings, same table and bullet formats.
   - **Section 10 — Compiled Synthesis:** ≤150 words, evidence-grounded summary drawn from `items_top5` and `stats_summary`.
   - **Section 11 — Opportunity Analysis:** ≤150 words, actionable opportunities drawn from the same data.
4. Open every chart PNG in the user's default image viewer. Extract PNG paths from `packet.chart_captions` (each caption contains a `_(see PNG: …)_` marker for scatter/table charts; bar/line PNGs live alongside under `~/.social-research-probe/charts/`). **Bar charts have no `_(see PNG: …)_` marker** — always explicitly include `~/.social-research-probe/charts/overall_score_bar.png`. On macOS run `open <path1> <path2> …`; on Linux use `xdg-open`; on Windows use `start`. Run this once before emitting output.
5. For each chart in section 8: include a clickable markdown link `[filename](full png path)` and attempt an inline preview via Claude Code's `Read` tool on the PNG path.
