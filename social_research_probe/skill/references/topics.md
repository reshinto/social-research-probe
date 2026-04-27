State: `topics.json`.

- Show: `srp show-topics [--output text|json|markdown]`
- Add: `srp update-topics --add TOPIC... [--force] [--output ...]`
- Add quoted list: `srp update-topics --add '"a"|"b"'`
- Remove: `srp update-topics --remove TOPIC...`
- Rename: `srp update-topics --rename OLD NEW`

Duplicate add exits `2`; retry only if user wants `--force`.
