1. `srp config check-secrets --needed-for research --platform youtube --output json` — if `missing` is non-empty, tell the user to run `srp config set-secret <name>` in a terminal (hidden prompt; never paste keys into chat). Stop until confirmed.
2. Decide whether the CLI or the host LLM should handle the language step:
   - If the user already gave an explicit topic + purpose, call the explicit `srp research` form directly.
   - If the user gave a natural-language query and `llm.runner != none`, call the CLI natural-language form.
   - If the user gave a natural-language query and `llm.runner = none`, classify it with the host LLM into a topic + purpose first, then call the explicit CLI form. Reuse existing topic/purpose names when they are semantically close.
3. Run one of:
   - `srp research <topic> <purpose>` — platform defaults to `youtube`.
   - `srp research <platform> <topic> <purpose1>,<purpose2>` — multiple purposes.
   - `srp research [<platform>] "<natural-language query>"` — CLI-side classification; use only when `llm.runner != none`.
4. Flags: `--no-shorts` excludes Shorts (<90s), `--no-transcripts` skips enrichment, `--no-html` skips HTML.
5. The CLI prints a ready-to-run `srp serve-report --report …` command. Surface that command to the user immediately.
6. Emit a brief Markdown summary of sections 1-9 inline. Do not re-emit the full report.
   - Section 3 — per top-N item: write a 1-2 sentence host-LLM summary from `packet.items_top_n[i].transcript`; fall back to `one_line_takeaway`.
7. For Compiled Synthesis, Opportunity Analysis, and Final Summary:
   - If `llm.runner != none` and the packet/report already contains synthesis, surface that output and do not duplicate it with the host LLM.
   - If `llm.runner = none`, use the host LLM to write Compiled Synthesis, Opportunity Analysis, and Final Summary inline from the packet.
   - If the user wants the rendered HTML updated with host-written synthesis, create text files from that host-written content and run `srp report --packet <json> --compiled-synthesis <file> --opportunity-analysis <file> --final-summary <file> --out <html>`. Author templates: `docs/synthesis-authoring.md` in the repo.
