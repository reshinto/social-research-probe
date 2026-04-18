# srp Command Reference

Invoke from Claude Code:

```text
/srp <intent>
```

## Command Map

| User asks about | Commands covered | Reference |
|---|---|---|
| topics | show-topics, update-topics | [topics.md](topics.md) |
| purposes | show-purposes, update-purposes | [purposes.md](purposes.md) |
| pending suggestions | show-pending, apply-pending, discard-pending | [pending.md](pending.md) |
| generating suggestions | suggest-topics, suggest-purposes | [suggest.md](suggest.md) |
| running research | run-research | [run-research.md](run-research.md) |

## Exit Codes

- `0` success (may include warnings)
- `2` validation / parse error
- `3` duplicate conflict (retry with `--force`)
- `4` adapter / subprocess failure
- `5` schema migration failure
