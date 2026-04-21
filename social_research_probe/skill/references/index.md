# srp Command Reference

Invoke from Claude Code as `/srp <intent>`.

## Command Map

| User asks about | Commands | Reference |
|---|---|---|
| topics | show-topics, update-topics | [topics.md](topics.md) |
| purposes | show-purposes, update-purposes | [purposes.md](purposes.md) |
| pending suggestions | show-pending, apply-pending, discard-pending | [pending.md](pending.md) |
| generating suggestions | suggest-topics, suggest-purposes, stage-suggestions | [suggest.md](suggest.md) |
| running research | research, report | [research.md](research.md) |
| config & secrets | config show/set/path/set-secret/unset-secret/check-secrets | [config.md](config.md) |
| advanced / setup | setup, install-skill, corroborate-claims, render | [advanced.md](advanced.md) |

Exit codes: `0` ok · `2` validation · `3` duplicate (retry `--force`) · `4` adapter/subprocess · `5` migration.
