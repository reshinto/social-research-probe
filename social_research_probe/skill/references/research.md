1. `srp config check-secrets --needed-for research --platform youtube --output json`
   If `missing` is non-empty: tell user to run `srp config set-secret <name>` in a terminal (hidden prompt — never ask them to paste keys into chat). Stop until confirmed.
2. Run the research:
   - `srp research --mode skill <topic> <purpose>` — platform defaults to `youtube`
   - `srp research --mode skill <platform> <topic> <purpose1>,<purpose2>` — multiple purposes (comma-separated)
   - Add `--no-shorts` to exclude YouTube Shorts (<90s). Shorts are included by default.
3. Parse the emitted JSON. Fill per `response_schema`:
   - `compiled_synthesis`: ≤150 words, evidence-grounded summary of findings
   - `opportunity_analysis`: ≤150 words, actionable opportunities
4. Open every chart PNG in the user's default image viewer so charts are visible outside the chat. Extract PNG paths from `packet.chart_captions` (each caption contains a `_(see PNG: …)_` marker for scatter/table; bar/line PNGs live next to them under `~/.social-research-probe/charts/`). **Bar charts have no `_(see PNG: …)_` marker** — always explicitly include `~/.social-research-probe/charts/overall_score_bar.png` in the open call. On macOS run `open <path1> <path2> …`; on Linux use `xdg-open`; on Windows use `start`. Run this once before emitting the summary so the viewer opens while the user reads.
5. Read `references/output-format.md` and emit sections 1–11 exactly as defined there. That file is the single source of truth for output structure — do not invent or skip any section.
