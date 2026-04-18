- Show: `srp show-topics` — print stdout.
- Add: `srp update-topics --add '"t1"|"t2"'`
- Remove: `srp update-topics --remove '"t1"|"t2"'`
- Rename: `srp update-topics --rename '"old"->"new"'`

Exit 3 on add = duplicate conflict; surface the match, offer `--force`.
