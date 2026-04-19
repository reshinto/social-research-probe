1. `srp config check-secrets --needed-for run-research --platform youtube --output json`
   If `missing` is non-empty: tell user to run `srp config set-secret <name>` in a terminal (hidden prompt — never ask them to paste keys into chat). Stop until confirmed.
2. Run the research. Prefer the simple form:
   - `srp research --mode skill <topic> <purpose>` — platform defaults to `youtube`
   - `srp research --mode skill <platform> <topic> <purpose1>,<purpose2>` — multiple purposes (comma-separated)
   - Add `--no-shorts` to exclude YouTube Shorts (<90s). Shorts are included by default.
   - Advanced multi-topic: `srp run-research --mode skill --platform youtube '"topic1"->p1+p2;"topic2"->p3'`
3. Parse the emitted JSON. Fill per `response_schema`:
   - `compiled_synthesis`: ≤150 words, evidence-grounded summary of findings
   - `opportunity_analysis`: ≤150 words, actionable opportunities
4. Emit stitched sections 1–11 to the user. Each chart in section 8 has a PNG path; render the PNG inline via the editor's image preview where possible.
