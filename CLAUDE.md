# Project Claude Rules

## Must-follow shortcuts

- Use `.venv/bin/*` for Python commands.
- Current repo files are source of truth.
- Read Obsidian project memory only when project context matters.
- Read `Framework Rules.md` before editing `platforms/`, `services/`, or `technologies/`.
- Use graphify for architecture/cross-module questions when `graphify-out/` exists.
- After code edits, run `graphify update .`.

## Obsidian memory

Vault project folder:

`~/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/reshinto-brain/10 Projects/social-research-probe/`

Relevant notes:

- project memory: `social-research-probe.md`
- project rules: `Project Rules.md`
- framework rules: `Framework Rules.md`
- plans: `Plans/`

Do not scan the whole vault unless explicitly asked.

## Python

Always use project-local tools:

```bash
.venv/bin/python
.venv/bin/pytest
.venv/bin/ruff
.venv/bin/mypy
```

## Framework boundary trigger

Before editing files under:

```text
social_research_probe/platforms/
social_research_probe/services/
social_research_probe/technologies/
```

read:

`~/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/reshinto-brain/10 Projects/social-research-probe/Framework Rules.md`

Ultra-short boundary summary:

```text
platforms    -> may import utils/services only; call services via execute_batch only
services     -> may import services/technologies/utils; never platforms; inherit BaseService; logic in execute_service; tech via _get_technologies
technologies -> may import technologies/utils only; never services/platforms; inherit BaseTechnology; logic in _execute
```

If a requested change violates this framework, stop and explain the conflict.

## graphify

If `graphify-out/` exists:

- architecture/codebase questions: read `graphify-out/GRAPH_REPORT.md`
- if `graphify-out/wiki/index.md` exists, use it before raw-file exploration
- cross-module questions: prefer graph traversal commands:

```bash
graphify query "<question>"
graphify path "<A>" "<B>"
graphify explain "<concept>"
```

After modifying code:

```bash
graphify update .
```

## Workflow

For non-trivial implementation work:

1. Read relevant repo files.
2. Read relevant Obsidian note only if needed.
3. Create/update an Obsidian plan only for multi-file, architectural, refactor, feature, or investigation-heavy work.
4. Make the smallest correct change.
5. Run relevant `.venv/bin/*` checks.
6. Summarize changes, checks, and follow-ups.

## Validation

When practical:

```bash
grep -R "from social_research_probe.platforms\|import social_research_probe.platforms" social_research_probe/services social_research_probe/technologies
grep -R "from social_research_probe.technologies\|import social_research_probe.technologies" social_research_probe/platforms
grep -R "from social_research_probe.services\|import social_research_probe.services" social_research_probe/technologies
.venv/bin/ruff check .
.venv/bin/pytest
```
