State: `pending_suggestions.json`.

- Show: `srp show-pending [--output text|json|markdown]`
- Apply: `srp apply-pending --topics IDS|all --purposes IDS|all`
- Discard: `srp discard-pending --topics IDS|all --purposes IDS|all`

`IDS` = comma ints from `show-pending`. Empty selector = none. Apply silently skips duplicates, then removes selected pending rows.
