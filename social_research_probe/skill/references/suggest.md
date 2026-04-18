Pattern for both topics and purposes:

1. `srp suggest-<topics|purposes> --output json` — generates rule-based candidates and auto-stages them.
2. Enhance and re-stage via stdin:
   - topics: `{"topic_candidates":[{"value":"...","reason":"..."}]}`
   - purposes: `{"purpose_candidates":[{"name":"...","method":"...","reason":"..."}]}`
3. `echo '<json>' | srp stage-suggestions --from-stdin`
