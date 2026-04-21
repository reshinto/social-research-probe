1. `srp config check-secrets --needed-for research --platform youtube --output json` — if `missing` is non-empty, tell the user to run `srp config set-secret <name>` in a terminal (hidden prompt; never paste keys into chat). Stop until confirmed.
2. Run one of:
   - `srp research <topic> <purpose>` — platform defaults to `youtube`.
   - `srp research <platform> <topic> <purpose1>,<purpose2>` — multiple purposes.
   - `srp research [<platform>] "<natural-language query>"` — auto-classifies into topic + purpose; requires `llm.runner != none`.
3. Flags: `--no-shorts` excludes Shorts (<90s), `--no-transcripts` skips enrichment, `--no-html` skips HTML.
4. The CLI prints `[srp] HTML report: file:///…` to stderr. Surface that path to the user immediately.
5. Emit a brief Markdown summary of sections 1–9 inline. Do not re-emit the full report.
   - Section 3 — per top-5 item: 1–2 sentence summary from `packet.items_top5[i].transcript`; fall back to `one_line_takeaway`.
   - Sections 10–11: skip inline if HTML already contains them (runner configured); otherwise see the authoring guide.
6. Custom sections 10–11 → `srp report --packet <json> --synthesis-10 <file> --synthesis-11 <file> --out <html>`. Author templates: `docs/synthesis-authoring.md` in the repo.
