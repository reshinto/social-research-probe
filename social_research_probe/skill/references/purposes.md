State: `purposes.json`. Purpose = name + method.

- Show: `srp show-purposes [--output text|json|markdown]`
- Add: `srp update-purposes --add NAME METHOD [--force]`
- Add DSL: `srp update-purposes --add '"name"="method"'`
- Remove: `srp update-purposes --remove NAME...`
- Remove DSL: `srp update-purposes --remove '"a"|"b"'`
- Rename: `srp update-purposes --rename OLD NEW`

New purpose gets empty `evidence_priorities` and `scoring_overrides`. Duplicate add exits `2`; retry only if user wants `--force`.
