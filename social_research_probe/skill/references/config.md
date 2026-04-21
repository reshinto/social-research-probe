- Show: `srp config show` — print current config.
- Path: `srp config path` — print resolved `config.toml` path.
- Set: `srp config set <dotted.key> <value>` — e.g. `srp config set llm.runner gemini`.
- Set secret: `srp config set-secret <NAME>` — opens a hidden prompt. Never ask the user to paste secrets into chat.
- Unset secret: `srp config unset-secret <NAME>`.
- Check secrets: `srp config check-secrets --needed-for research --platform <name> --output json` — returns `{"missing":[...]}`. Use before research.

Secrets live in `secrets.toml` (mode `0600`). `SRP_SECRET_<NAME>` env vars override the file.
