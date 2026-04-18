- Show: `srp show-purposes` — print stdout.
- Add: `srp update-purposes --add '"name"="method description"'`
- Remove: `srp update-purposes --remove '"n1"|"n2"'`
- Rename: `srp update-purposes --rename '"old"->"new"'`

Exit 3 on add = duplicate conflict; surface the match, offer `--force`.
