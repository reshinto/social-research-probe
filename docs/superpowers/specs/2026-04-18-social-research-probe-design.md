# SocialResearchProbe — Design Spec

**Status:** design finalized via brainstorming dialogue 2026-04-18, revised after feedback
on references layout and LLM routing. Intended to be moved to
`docs/superpowers/specs/2026-04-18-social-research-probe-design.md` after plan mode exits.

---

## Context

`/Users/springfield/dev/social-research-probe` is empty. Greenfield design for an
evidence-first social-media research system. Output as **one Claude Code skill** +
**one CLI** + **one shared Python backend**. Initially targets YouTube; must be
trivially extensible to TikTok/X/Reddit/etc. Must minimize tokens by keeping the LLM
out of every deterministic step.

## Hard Invariants (non-negotiable)

1. **Skill mode makes ZERO external LLM calls.** Every LLM-requiring step
   (synthesis, opportunity analysis, suggestion enhancement, claim corroboration)
   is redirected to the host LLM that activated the skill — by emitting a JSON
   packet via stdout and letting the host LLM produce the final content. The skill
   never imports an LLM SDK; the CLI never makes an HTTP/LLM API call while
   `--mode skill` is set. A contract test enforces this by asserting
   `subprocess.run` is never called from any code reachable under `--mode skill`
   when the mock-networks layer is engaged.
2. **CLI mode uses LLMs only via their CLI binaries.** If an LLM is configured, the
   backend invokes its command-line tool via subprocess (`claude`, `gemini`,
   `codex`/`openai`, `ollama`). There are no Python SDK dependencies for LLMs —
   `pyproject.toml` lists no `anthropic`, `openai`, `google-generativeai`, etc.
   A contract test asserts those packages are not importable from the source tree.
3. **Non-LLM APIs (YouTube Data, Exa, Brave, Tavily) are unaffected by these
   invariants.** They are HTTP data sources, not LLMs. They remain pluggable and
   optional.

These invariants are load-bearing for every section below.

## Decisions (from brainstorming)

| # | Decision |
|---|---|
| Q1 | **Python** (strong stats/viz ecosystem) |
| Q2 | **Full spec upfront**; phased build |
| Q3 | **Data dir configurable**: `--data-dir` > `SRP_DATA_DIR` > `./.skill-data/` (if exists) > `~/.social-research-probe/` |
| Q4 | **Corroboration pluggable**; default backend = configured LLM; switchable to Exa / Brave / Tavily |
| Q5 | **LLM routing by mode.** Skill mode: all LLM work is done by the host LLM that activated the skill (no external calls, no API keys needed). CLI mode: shell out to external LLM CLIs via subprocess (no SDK integration). |
| Q6 | **Suggestions**: rule-based fallback + optional LLM enhancement (via host LLM in skill mode; via subprocess in CLI mode) |
| Q7 | **CLI framework**: argparse (stdlib, zero extra dep) |
| Q8 | **LLM CLIs (CLI mode)**: `claude`, `gemini`, `codex`/`openai`, `ollama` — all invoked as subprocesses. Pattern mirrors https://github.com/reshinto/gemini-skill. |
| Q9 | **YouTube fetch**: Data API v3 for metadata + yt-dlp for transcripts on demand |
| Q10 | **Distribution**: both `pipx install` and project venv documented |
| Q11 | **Default output**: `text` |
| Q12 | **Architecture**: single installable package with internal registries |
| Q13 | **References layout**: one file per subcommand (`references/run-research.md`, `references/update-topics.md`, etc.); `SKILL.md` stays tiny and only loads the relevant reference at invocation. |

---

## 1. Architecture

```
             ┌──────────────────────────── SKILL mode ─────────────────────────────┐
User (skill) → SKILL.md → [host LLM] shells to `srp ... --mode skill` (JSON packet)
             │                    │ fills sections 10+11, generates suggestions,
             │                    │ corroborates claims — all inline in host LLM
             │                    ▼
             └────────── stitched output returned to the user ────────────────────┘

             ┌──────────────────────────── CLI mode ───────────────────────────────┐
CLI user   →  srp ... --mode cli (default when invoked outside skill)
                                  │
                                  └→ subprocess: `claude -p '<prompt>'`
                                                 `gemini -p '<prompt>'`
                                                 `codex ...`  /  `openai ...`
                                                 `ollama run <model> '<prompt>'`
             └────────── stitched output printed to stdout ───────────────────────┘

Both modes share one backend:
   social_research_probe/
     ├─ state            (atomic JSON)
     ├─ platforms/       (YouTube first)
     ├─ llm/runners/     (subprocess wrappers; NOT SDK clients)
     ├─ llm/host.py      (in-skill passthrough; emits packet for host LLM)
     ├─ corroboration/   (mode-aware: host/subprocess/Exa/Brave/Tavily)
     ├─ scoring · stats · viz   (pure code)
     └─ synthesize/      (templates; 1 synthesis call per research run)
```

**Core invariant.** `pipeline.run_research()` and everything it calls consume only
abstractions from four registries (`platforms`, `llm_runners`, `corroboration`,
suggestions). Zero platform/provider name branches outside each subpackage. A
lint-style contract test enforces this.

**Mode-dispatch rule.** The pipeline is identical up to step 14. At step 14:
- `--mode skill` returns a `SkillPacket` (JSON) via stdout and exits 0 without any
  LLM call. The host LLM (Claude Code running the skill) reads the packet, fills
  sections 10 + 11, and emits the stitched output.
- `--mode cli` shells out to the configured LLM CLI runner, parses the response
  against the JSON schema, and stitches the final output in the backend.

Default `--mode` = `cli` when `srp` is run from a terminal; the skill always passes
`--mode skill` explicitly.

**Degradation ladder.**
- Skill mode always has an LLM (the host).
- CLI mode with no runner configured → rule-based suggestions + skipped sections
  10–11 with note.
- Corroboration backend unavailable → claims `unverified` + section 5 flagged.
- YouTube API key missing → actionable error (exit 4).

---

## 2. Responsibility Split

| Responsibility | Owner | Agnostic? | Notes |
|---|---|---|---|
| Command DSL → dataclass | code `commands/parse.py` | ✅ | Hand-rolled recursive-descent; never LLM |
| State I/O / validate / migrate | code `state/` | ✅ | Atomic writes; `jsonschema`; versioned migrators + backups |
| Duplicate detection | code `dedupe.py` | ✅ | `rapidfuzz`, thresholds in config |
| Rule-based suggestion candidates | code `commands/suggestions.py` | ✅ | Gaps in topic×purpose matrix |
| LLM-enhanced suggestions | host LLM (skill) / subprocess runner (CLI) | ✅ | Optional; degrades to rule-based |
| Suggestion staging / apply / discard | code `commands/suggestions.py` | ✅ | Never auto-applies |
| Purpose merging | code `purposes/merge.py` | ✅ | Union evidence_priorities; concat methods; union model/chart sets; strictest scoring override |
| Platform dispatch | code `platforms/registry.py` | ✅ | Single call site |
| YouTube fetch | code `platforms/youtube/` | Specific | API v3 + lazy yt-dlp for transcripts |
| Source classification | code `validation/source.py` | Mostly agnostic | Adapter `TrustHints` + URL heuristics |
| AI-slop detection | code `validation/ai_slop.py` | Mostly agnostic | Title templating, cadence anomalies, missing citations, synthetic-voice metadata |
| Claim extraction | code `validation/claims.py` | ✅ | Deterministic sentence-split + key-phrase extraction on top-10 |
| Corroboration lookup | mode-aware `corroboration/*` | ✅ | Skill: host LLM judges claims via packet. CLI: LLM runner subprocess OR Exa/Brave/Tavily via HTTP. |
| Trust / trend / opportunity / overall scoring | code `scoring/*` | ✅ | Weights in config; per-purpose overrides |
| Model selection | code `stats/selector.py` | ✅ | Lookup + data-fit guard; never LLM |
| Statistical computation | code `stats/*` | ✅ | numpy / scipy / statsmodels |
| Visualization | code `viz/*` | ✅ | matplotlib PNG to `.skill-data/charts/{session_id}/`; degrades to spec+table |
| Output sections 1–9 | code `synthesize/formatter.py` | ✅ | Jinja/f-strings |
| **Section 10 (compiled synthesis)** | **host LLM (skill) / subprocess runner (CLI)** | ✅ | ≤150 words, strict JSON schema |
| **Section 11 (opportunity)** | **host LLM (skill) / subprocess runner (CLI)** | ✅ | ≤150 words; combined with section 10 in one call |
| Output stitching | code `synthesize/formatter.py` (CLI mode) / host LLM + skill template (skill mode) | ✅ | `text` / `markdown` / `json` |

**Token consequence.**
- Skill mode: **zero external LLM tokens**. Host LLM consumes 1 packet per research
  run (≤1.5k tokens) + 1 suggestion prompt when `suggest-*` runs. State commands
  cost 0 host-LLM tokens because the skill streams CLI stdout through verbatim.
- CLI mode: one subprocess LLM call per research run; state commands cost 0.

---

## 3. Storage & Schema

**Paths resolved once at CLI entry.**

Files:

```jsonc
// topics.json
{"schema_version": 1, "topics": ["ai agents", "robotics"]}

// purposes.json
{
  "schema_version": 1,
  "purposes": {
    "trends": {
      "method": "Track emergence across channels, velocity, saturation",
      "evidence_priorities": ["view velocity", "repeated emergence", "upload date"],
      "scoring_overrides": {}
    }
  }
}

// pending_suggestions.json
{
  "schema_version": 1,
  "pending_topic_suggestions": [
    {"id": 1, "value": "on-device LLMs", "reason": "gap",
     "duplicate_status": "new", "matches": []}
  ],
  "pending_purpose_suggestions": [
    {"id": 1, "name": "saturation-analysis", "method": "...",
     "evidence_priorities": ["..."],
     "duplicate_status": "near-duplicate", "matches": ["trends"]}
  ]
}
```

Subdirs:

- `cache/`                — platform responses, SHA-keyed, TTL 6h search / 24h channel
- `charts/{session_id}/`  — rendered PNGs
- `sessions/{id}.json`    — archived packet + final output for `render-research`
- `.backups/{file}.v{N}.{ts}.json` — pre-migration backups

**Lifecycle rules:**

1. **Read.** Missing file ⇒ seed defaults at current version. Missing
   `schema_version` ⇒ treat as 0. Run migrators in order.
2. **Migrate.** `state/migrate.py` holds ordered `MIGRATORS = [m_0_1, m_1_2, ...]`.
   Pure, idempotent; writes backup before overwriting.
3. **Validate.** `jsonschema` strict. Runs post-read, post-migrate, pre-write.
   Failure → exit 2.
4. **Write.** Serialize → `{file}.tmp` → `fsync` → `os.replace` (POSIX atomic).
   Topics sorted alphabetical. Pending IDs ascending. `indent=2`,
   `ensure_ascii=False`, LF endings.
5. **Unknown future version.** Exit 5, don't touch file.
6. **ID allocation.** `max(existing_ids) + 1`; never reuse; never resort mid-file.

---

## 4. Platform Adapter Contract

```python
@dataclass(frozen=True)
class FetchLimits:
    max_items: int = 20
    recency_days: int | None = 90

@dataclass(frozen=True)
class RawItem:
    id: str; url: str; title: str
    author_id: str; author_name: str
    published_at: datetime
    metrics: dict
    text_excerpt: str | None
    thumbnail: str | None
    extras: dict

@dataclass(frozen=True)
class SignalSet:
    views: int | None; likes: int | None; comments: int | None
    upload_date: datetime | None
    view_velocity: float | None
    engagement_ratio: float | None
    comment_velocity: float | None
    cross_channel_repetition: float | None
    raw: dict

@dataclass(frozen=True)
class TrustHints:
    account_age_days: int | None
    verified: bool | None
    subscriber_count: int | None
    upload_cadence_days: float | None
    citation_markers: list[str]

class PlatformAdapter(ABC):
    name: ClassVar[str]
    default_limits: ClassVar[FetchLimits]
    @abstractmethod
    def health_check(self) -> bool: ...
    @abstractmethod
    def search(self, topic: str, limits: FetchLimits) -> list[RawItem]: ...
    @abstractmethod
    def enrich(self, items: list[RawItem]) -> list[RawItem]: ...
    @abstractmethod
    def to_signals(self, items: list[RawItem]) -> list[SignalSet]: ...
    @abstractmethod
    def trust_hints(self, item: RawItem) -> TrustHints: ...
    @abstractmethod
    def url_normalize(self, url: str) -> str: ...
    def fetch_text_for_claim_extraction(self, item: RawItem) -> str | None:
        return None
```

**Registry (`platforms/registry.py`)**: module-level `_REGISTRY`; `@register`
decorator; `get_adapter(name, config)`.

**YouTube (first adapter):**
- `fetch.py` — `google-api-python-client`: `search.list` → `videos.list` →
  `channels.list`; backoff; cached.
- `extract.py` — `yt-dlp` only on `fetch_text_for_claim_extraction()`.
- `trust_hints.py` — channel age, verified flag, subscriber count, description URLs.

**Adding a platform:** new subpackage + `@register` + `SignalSet` mapping + contract
tests. Zero core edits.

---

## 5. LLM Routing — Mode-Aware

There is **no SDK-based LLM client** in this project. Instead there are two
interchangeable interfaces.

### 5.1 Host-LLM passthrough (skill mode)

`llm/host.py` exposes a single function:

```python
def emit_packet(packet: dict, kind: Literal["synthesis","suggestions","corroboration"]) -> NoReturn:
    """Print the packet as JSON to stdout with a typed envelope, exit 0.
       The host LLM reads stdout and produces the final output per the
       reference doc for this command.
    """
    json.dump({"skill_mode": True, "kind": kind, "packet": packet}, sys.stdout)
    sys.exit(0)
```

This is the only "LLM API" in skill mode. The host LLM (Claude running the skill)
performs the synthesis work based on instructions in `references/<subcommand>.md`.

### 5.2 Subprocess runner (CLI mode)

```python
@dataclass(frozen=True)
class LLMRequest:
    system: str                 # combined into prompt per-runner
    user: str
    response_schema: dict       # enforced via JSON-only prompt + validation
    max_tokens: int = 600

@dataclass(frozen=True)
class LLMResponse:
    data: dict                  # validated per response_schema
    raw_stdout: str
    runner: str

class LLMRunner(ABC):
    name: ClassVar[str]
    @abstractmethod
    def available(self) -> bool: ...     # checks the CLI binary exists on PATH
    @abstractmethod
    def complete(self, req: LLMRequest) -> LLMResponse: ...
```

Each runner is a thin shell wrapper. No `anthropic`/`openai`/`google-generativeai`
Python SDK dependencies.

**Shipped runners:**

| Runner | Binary | Invocation pattern | Notes |
|---|---|---|---|
| `claude` | `claude` | `claude -p "<prompt>" --output-format json --model sonnet` | Official Claude CLI. Prompt prepends the system+user+schema. |
| `gemini` | `gemini` | `gemini -p "<prompt>" --output-format json` | Follows reshinto/gemini-skill shell pattern. |
| `codex` | `codex` or `openai` | `codex -p "<prompt>"` OR `openai api chat.completions.create -m gpt-4o ...` | Configurable per-user since OpenAI CLI landscape is fragmented. |
| `local` | `ollama` (and compatibles) | `ollama run <model> "<prompt>"` | Read model from config.toml. |

Runner contract:
- Prompt serialized with explicit `OUTPUT MUST BE VALID JSON MATCHING THIS SCHEMA:`
  section appended (no SDK-level schema enforcement exists for CLIs).
- Runner pipes prompt via stdin when the CLI supports it, else via `-p` flag.
- On non-zero exit or timeout (default 60s): typed failure.
- On non-JSON stdout or schema violation: retry once with a "you returned
  non-conforming JSON" addendum; on second failure, typed failure.
- Typed failure in `run-research`: sections 10–11 render "LLM synthesis unavailable"
  and pipeline continues (exit 0 with warning).

**Runner selection:** `--llm` flag > `config.toml llm.runner` > first registered
`available()` > `none`. Each runner's `available()` checks `shutil.which(binary)` +
any extra health-checks documented per runner.

**Config shape (`config.toml`):**

```toml
[llm]
runner = "claude"           # or "gemini", "codex", "local", "none"

[llm.claude]
model = "sonnet"            # passed as `--model`
extra_flags = []

[llm.gemini]
model = "gemini-2.5-pro"
extra_flags = []

[llm.codex]
binary = "codex"            # or "openai"
model = "gpt-4o"
extra_flags = []

[llm.local]
binary = "ollama"
model = "llama3.1:8b"
extra_flags = []

[llm.timeout_seconds] = 60
```

### 5.3 Corroboration backends

Same mode-aware pattern:

```python
class CorroborationBackend(ABC):
    name: ClassVar[str]
    def available(self) -> bool: ...
    def check(self, claims: list[Claim]) -> list[CorroborationResult]: ...
```

**Shipped backends:**
- `host` (skill mode default) — emits a corroboration packet; host LLM returns
  JSON; backend parses into `CorroborationResult[]`.
- `llm_cli` (CLI mode default) — routes claims through the configured `LLMRunner`.
- `exa` / `brave` / `tavily` — HTTP search APIs. Post-process with configured
  LLM runner (CLI mode) or host LLM (skill mode).

**Cost cap:** ≤5 claims per item, ≤15 claims per session.

---

## 6. Scoring, Statistics, Visualization

### Scoring formulas (all in `[0,1]`)

```
trust_score = 0.35·source_class
            + 0.25·channel_credibility
            + 0.15·citation_traceability
            + 0.15·(1 - ai_slop_penalty)
            + 0.10·corroboration_score    # validated=1, partial=0.6, unverified=0.3, low-trust=0

trend_score = 0.40·z(view_velocity)
            + 0.20·z(engagement_ratio)
            + 0.20·z(cross_channel_repetition)
            + 0.20·recency_decay          # exp(-age_days/30)

opportunity_score = 0.40·market_gap
                  + 0.30·monetization_proxy
                  + 0.20·feasibility
                  + 0.10·novelty

overall = 0.45·trust + 0.30·trend + 0.25·opportunity
```

Weights in `config.toml [scoring.weights]`. Purposes may override via
`purposes.<name>.scoring_overrides`. Merge rule: element-wise max. Invariant: high
trend cannot compensate for low trust (asserted by property-based tests).

### Model selection (`stats/selector.py`)

| Purpose keyword | Models |
|---|---|
| `trends` / growth / emergence | linear regression on `view_velocity ~ upload_date`, rolling 7/30-day avgs, ranking |
| `job` / career | descriptive, correlation (engagement × recency), ranking |
| `arbitrage` / spread | IQR spread, modified-z outlier |
| combined | union, deduped by class, cap 3 |
| fallback (`n<5` or near-zero variance) | descriptive only + `low_confidence=true` |

### Chart selection (`viz/selector.py`)

| Purpose class | Charts |
|---|---|
| trend | line (time series), bar (top-scored items) |
| job | bar (rank), table |
| arbitrage | scatter + spread table |
| default | table |

matplotlib; cap 3 per session; degrades to `ChartSpec + table` when `n<3` or
required fields all-None.

---

## 7. Research Pipeline

`pipeline.run_research(parsed_command, mode) → ResearchResult`. Steps 1–13 run
identically in both modes; step 14 branches on mode.

1. `purposes.merge(purpose_set)` → `MergedPurpose`.
2. `platforms.registry.get_adapter(platform)`; `health_check()`.
3. `adapter.search(topic, limits)` → `≤20 RawItem` (cache-aware).
4. `adapter.enrich(items)`.
5. `adapter.to_signals(items)`; compute `cross_channel_repetition` batch-wide.
6. `validation.source.classify(items)`.
7. `validation.ai_slop.assess(items)`.
8. `validation.claims.extract(top10)` → `≤15 Claim`;
   `corroboration.backend.check(claims)` (mode-aware per §5.3).
9. `scoring.combine.score_all(...)`.
10. Rank by `overall`; keep top 5.
11. `stats.run(merged.model_set, items_top5, signals)` → `StatReport[]`.
12. `viz.render(merged.chart_set, items_top5, signals)` → `ChartArtifact[]`.
13. Build synthesis packet (target <1.5k tokens):

    ```json
    {
      "topic": "...",
      "platform": "youtube",
      "purpose_set": ["trends","job-opportunities"],
      "items_top5": [{"title":..., "channel":..., "url":...,
                      "source_class":..., "scores":{...},
                      "one_line_takeaway":"..."}],
      "source_validation_summary": {"validated":2,"partially":1,
        "unverified":1,"low_trust":1,"primary":2,"secondary":2,
        "commentary":1,"notes":"..."},
      "platform_signals_summary": "...",
      "evidence_summary": "...",
      "stats_summary": {"models_run":[...], "highlights":[...],
                        "low_confidence": false},
      "chart_captions": ["...","..."],
      "warnings": [],
      "response_schema": {
        "compiled_synthesis": "string ≤150 words",
        "opportunity_analysis": "string ≤150 words"
      }
    }
    ```

14. **Mode branch:**
    - **Skill mode** (`--mode skill`): emit `SkillPacket(kind="synthesis", packet=<above>)`
      to stdout via `llm.host.emit_packet`; exit 0. Host LLM reads the packet, follows
      `references/run-research.md`, and produces the final stitched output. No
      subprocess, no external API.
    - **CLI mode** (`--mode cli`): call `runner.complete(LLMRequest(...))` against
      the configured runner. Retry-once-on-violation. Stitch sections 1–11 via
      `synthesize/formatter.py`. Output per `--output` flag.

15. Persist `sessions/{session_id}.json` with the packet + (CLI only) the runner
    response, for later `render-research`.

**Shared-work optimization.** Steps 2–8 run once per topic, not once per purpose.
Divergence happens at step 9 (override weights) and steps 11–12 (purpose-merged
model/chart sets).

---

## 8. Purpose Composition

Given purposes `P1…Pn`:

- `method = "\n".join(unique_first_seen(P.method))`
- `evidence_priorities = union_preserve_order(P.evidence_priorities)`
- `model_set = union(stats.selector.for_purpose(P)) deduped by class`
- `chart_set = union(viz.selector.for_purpose(P)) capped at 3`
- `scoring_overrides = element-wise max` — strictest trust wins

---

## 9. Commands & CLI

**Command DSL (parsed by `commands/parse.py`):**

```
update-topics add:"a"|"b"
update-topics remove:"a"|"b"
update-topics rename:"old"->"new"
show-topics
update-purposes add:"name"="method summary"
update-purposes remove:"a"|"b"
update-purposes rename:"old"->"new"
show-purposes
suggest-topics
suggest-purposes
show-pending-suggestions
apply-pending-suggestions topics:all|1,3 purposes:all|2,4
discard-pending-suggestions topics:all|1,3 purposes:all|2,4
run-research platform:youtube "topic"->p1+p2;"topic2"->p3
```

**CLI (`cli.py`, argparse):**

```
srp update-topics   --add '"a"|"b"' | --remove '"a"|"b"' | --rename '"old"->"new"'
srp show-topics
srp update-purposes --add 'name=method' | --remove '"a"|"b"' | --rename '"old"->"new"'
srp show-purposes
srp suggest-topics  [--count 5] [--use-llm/--no-use-llm]
srp suggest-purposes [--count 5] [--use-llm/--no-use-llm]
srp show-pending
srp apply-pending   [--topics all|IDS] [--purposes all|IDS]
srp discard-pending [--topics all|IDS] [--purposes all|IDS]
srp run-research    --platform NAME "topic->p1+p2;topic2->p3" [--top-n 5]
srp parse           "<raw>"                       # used by skill
srp stage-suggestions --from-stdin                # used after host LLM (skill) or runner (CLI) returns candidates
srp render-research <session-id>
srp config show | path | set <k> <v> | set-secret <name> [--from-stdin]
                | unset-secret <name> | check-secrets [--needed-for CMD] [--platform N] [--corroboration N]
```

**Global flags:**
`--mode {skill,cli}` (default `cli`; skill passes `skill` explicitly).
`--output {text,json,markdown}` (default `text`).
`--data-dir PATH`.
`--llm {claude,gemini,codex,local,none}` (CLI mode only; ignored in skill mode).
`--corroboration {host,llm_cli,exa,brave,tavily,none}` (default picks `host` in
skill mode, `llm_cli` in CLI mode).
`--verbose`.

**Exit codes:**
- `0` success (may include warnings)
- `2` validation / parser error
- `3` duplicate conflict (retry with `--force`)
- `4` adapter / network / subprocess failure (missing CLI binary falls here with a
  clear hint)
- `5` schema migration failure

**Confirmation:** `apply-pending` requires explicit IDs or `all`. `update-topics
add` on near-duplicate exits 3; `--force` overrides.

---

## 10. Skill (minimal SKILL.md + per-subcommand references)

`SocialResearchProbe/SKILL.md` (≤40 lines; only loaded content until triggered):

```markdown
---
name: SocialResearchProbe
description: Evidence-first social-media research via the `srp` CLI. Triggers on
  update-topics, update-purposes, show-topics, show-purposes, suggest-topics,
  suggest-purposes, show-pending-suggestions, apply-pending-suggestions,
  discard-pending-suggestions, run-research.
---

# SocialResearchProbe

Shell out to `srp`; never reimplement logic. Always pass `--mode skill` so the CLI
emits a packet instead of calling an external LLM.

## Command → reference

| User command                    | Reference file                        |
|---------------------------------|---------------------------------------|
| update-topics                   | references/update-topics.md           |
| show-topics                     | references/show-topics.md             |
| update-purposes                 | references/update-purposes.md         |
| show-purposes                   | references/show-purposes.md           |
| suggest-topics                  | references/suggest-topics.md          |
| suggest-purposes                | references/suggest-purposes.md        |
| show-pending-suggestions        | references/show-pending.md            |
| apply-pending-suggestions       | references/apply-pending.md           |
| discard-pending-suggestions     | references/discard-pending.md         |
| run-research                    | references/run-research.md            |

1. Identify the user's command.
2. Read the matching reference file.
3. Follow its instructions exactly.
4. Report CLI stdout verbatim on non-zero exit surface stderr + exit code.
```

**Reference files — one per subcommand:**

| File | Loaded when | Content |
|---|---|---|
| `references/update-topics.md` | user runs update-topics | exact `srp` command shapes for add/remove/rename; how to surface dedupe exit-3 results |
| `references/show-topics.md` | user runs show-topics | call `srp show-topics --mode skill --output text`; print verbatim |
| `references/update-purposes.md` | user runs update-purposes | add/remove/rename syntax; method-string handling |
| `references/show-purposes.md` | user runs show-purposes | call + print |
| `references/suggest-topics.md` | user runs suggest-topics | call `srp suggest-topics --mode skill --output json` which returns rule-based drafts + a packet asking the host LLM to enhance; host LLM produces candidates matching the JSON schema and pipes them back via `srp stage-suggestions --from-stdin` |
| `references/suggest-purposes.md` | user runs suggest-purposes | same pattern as above for purposes |
| `references/show-pending.md` | user runs show-pending-suggestions | call + print |
| `references/apply-pending.md` | user runs apply-pending-suggestions | ID parsing rules; dedupe re-check surface |
| `references/discard-pending.md` | user runs discard-pending-suggestions | ID parsing rules |
| `references/run-research.md` | user runs run-research | pre-flight `srp config check-secrets --needed-for run-research --platform youtube --output json`; if `missing` is non-empty, instruct the user to run `srp config set-secret <name>` in their terminal (never ask them to paste the key into chat) and stop; otherwise call `srp run-research --mode skill`; parse packet; fill `compiled_synthesis` (≤150 words) + `opportunity_analysis` (≤150 words) per schema; if packet contains `kind=corroboration` sub-packet, judge claims first and pipe results back via `srp corroborate-claims --from-stdin` (internal helper); finally emit stitched sections 1–11 |

**Token consequence when skill is listed but not triggered:** only frontmatter +
~40 lines of body + the command→reference table. Each invocation loads exactly one
additional reference file (typically <100 lines).

---

## 11. Repository Layout

```
social-research-probe/
├── pyproject.toml
├── README.md
├── LICENSE
├── config.toml.example
├── .skill-data/
│   ├── topics.json
│   ├── purposes.json
│   ├── pending_suggestions.json
│   ├── cache/
│   ├── charts/
│   ├── sessions/
│   └── .backups/
├── SocialResearchProbe/
│   ├── SKILL.md
│   └── references/
│       ├── update-topics.md
│       ├── show-topics.md
│       ├── update-purposes.md
│       ├── show-purposes.md
│       ├── suggest-topics.md
│       ├── suggest-purposes.md
│       ├── show-pending.md
│       ├── apply-pending.md
│       ├── discard-pending.md
│       └── run-research.md
├── src/social_research_probe/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── errors.py
│   ├── pipeline.py
│   ├── commands/
│   │   ├── parse.py
│   │   ├── topics.py
│   │   ├── purposes.py
│   │   ├── suggestions.py
│   │   ├── research.py
│   │   ├── corroborate_claims.py     # internal helper for skill-mode corroboration
│   │   ├── config.py                 # srp config show/path/set/set-secret/unset-secret/check-secrets
│   │   └── render.py
│   ├── state/
│   │   ├── store.py
│   │   ├── schemas.py
│   │   ├── validate.py
│   │   └── migrate.py
│   ├── dedupe.py
│   ├── purposes/
│   │   ├── registry.py
│   │   └── merge.py
│   ├── platforms/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── signals.py
│   │   └── youtube/
│   │       ├── __init__.py
│   │       ├── adapter.py
│   │       ├── fetch.py
│   │       ├── extract.py
│   │       └── trust_hints.py
│   ├── llm/
│   │   ├── base.py               # LLMRunner ABC
│   │   ├── registry.py
│   │   ├── host.py               # skill-mode packet emitter
│   │   ├── prompts.py            # prompt templates
│   │   └── runners/
│   │       ├── claude.py         # subprocess: `claude`
│   │       ├── gemini.py         # subprocess: `gemini`
│   │       ├── codex.py          # subprocess: `codex` or `openai`
│   │       └── local.py          # subprocess: `ollama`
│   ├── corroboration/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── host.py               # skill-mode
│   │   ├── llm_cli.py            # CLI mode via runner
│   │   ├── exa.py
│   │   ├── brave.py
│   │   └── tavily.py
│   ├── validation/
│   │   ├── source.py
│   │   ├── ai_slop.py
│   │   └── claims.py
│   ├── scoring/
│   │   ├── trust.py
│   │   ├── trend.py
│   │   ├── opportunity.py
│   │   └── combine.py
│   ├── stats/
│   │   ├── selector.py
│   │   ├── descriptive.py
│   │   ├── growth.py
│   │   ├── regression.py
│   │   ├── correlation.py
│   │   ├── spread.py
│   │   └── outliers.py
│   ├── viz/
│   │   ├── selector.py
│   │   ├── line.py
│   │   ├── bar.py
│   │   ├── scatter.py
│   │   └── table.py
│   ├── synthesize/
│   │   ├── llm_contract.py
│   │   └── formatter.py
│   └── utils/
│       ├── hashing.py
│       ├── cache.py
│       ├── subprocess_runner.py   # shared subprocess helper: timeouts, stdin, stdout capture
│       └── io.py
├── tests/
│   ├── fixtures/
│   │   ├── youtube_responses/
│   │   └── llm_runners/           # captured stdout/stderr for each runner
│   ├── unit/
│   ├── integration/
│   └── contract/
└── docs/
    ├── architecture.md
    ├── adding-a-platform.md
    ├── adding-an-llm-runner.md
    ├── adding-a-corroboration-backend.md
    └── schema.md
```

---

## 12. Error Handling

| Failure | Module | User message | Exit |
|---|---|---|---|
| Invalid JSON on disk | `state/store.py` | short msg + backup path | 5 |
| Schema mismatch | `state/validate.py` | validation errors list | 2 |
| Unknown schema version | `state/migrate.py` | `unsupported schema_version=N` | 5 |
| DSL parse error | `commands/parse.py` | expected-shape hint | 2 |
| Duplicate on add | `commands/*` + `dedupe.py` | match details; `--force` | 3 |
| Unsupported platform | `platforms/registry.py` | list of registered adapters | 2 |
| Adapter health/quota | adapter | actionable hint | 4 |
| LLM CLI binary not found (CLI mode) | `llm/runners/*.available()` | "binary X not on PATH; set `llm.runner` or install" | 4 |
| LLM subprocess timeout / non-zero exit | `utils/subprocess_runner.py` | runner + stderr tail | 4 (hard) or 0 (warn, if synthesis only) |
| LLM returns non-JSON or schema violation twice | `llm/runners/*` | "LLM synthesis skipped — invalid response" | 0 (warn) |
| Corroboration unavailable | `corroboration/*` | "claims unverified" note | 0 (warn) |
| All items low-trust | pipeline | `warnings:[low_trust_dominant]`; host/runner told to hedge | 0 (warn) |
| Low statistical confidence | `stats/*` | `low_confidence=true` in report | 0 (warn) |
| No viable chart | `viz/*` | spec + table only | 0 |

LLM (host or runner) never sees stack traces — only the compact `warnings: []` list.

---

## 13. Testing

- **Unit (`tests/unit/`)** — parser grammar, state atomic writes, schema validation,
  migrator chains, dedupe thresholds, purpose merge, scoring math (table-driven),
  each stats module (fixed input → known output), viz spec assertions.
- **Fixture adapters (`tests/fixtures/youtube_responses/`)** — `FakeYouTubeAdapter`
  with recorded JSON; default in CI so tests run offline.
- **Fixture runners (`tests/fixtures/llm_runners/`)** — captured `(stdin, argv) →
  stdout, stderr, exit_code` tuples. Tests inject a `FakeSubprocessRunner` that
  looks up fixtures, bypassing real CLIs.
- **Integration (`tests/integration/`)** — `srp run-research --mode cli` via
  fake adapter + fake runner; golden-file comparison for the stitched output.
- **Skill-mode integration** — `srp run-research --mode skill` emits a packet that
  matches the packet JSON schema; a separate test simulates a host LLM response
  and verifies the skill's stitching instructions (from `references/run-research.md`)
  produce the expected stitched output.
- **Contract (`tests/contract/`)** — every registered `PlatformAdapter`,
  `LLMRunner`, `CorroborationBackend` passes a shared contract suite. Lint
  assertion: no non-adapter module imports a specific adapter/runner/backend.
- **Migration tests** — each `N→N+1` migrator has fixture pair + round-trip test.
- **Property-based (`hypothesis`)** — scoring monotonicity; trust dominance over trend.
- **LLM-runner tests** — mock `subprocess.run`; assert argv shape, prompt content,
  retry behavior on non-JSON stdout, timeout handling.
- **CLI tests** — argparse in-process dispatch; golden stdout/stderr per subcommand
  and output mode.

**Coverage target:** ≥85% line coverage on `src/social_research_probe/` excluding
live-subprocess and live-network paths.

---

## 14. Phased Build

| Phase | Scope | Deliverable | Deferred |
|---|---|---|---|
| **P0** | Scaffold | `pyproject.toml`, tree, argparse stub, CI, lint, empty SKILL.md + reference stubs | all logic |
| **P1** | State + commands + config/secrets | `state/`, `commands/{parse,topics,purposes,suggestions,config}.py`, `dedupe.py`, `~/.social-research-probe/secrets.toml` storage with 0600 perms, `srp config` subcommand suite, CLI wiring for state commands, unit tests | pipeline |
| **P2** | YouTube adapter + pipeline shell | `platforms/{base,registry,signals,youtube/*}`, `pipeline.py` steps 1–13 + sections 1–7 format; fake adapter; integration tests. `run-research --mode skill` emits a valid packet. | stats, viz, corroboration |
| **P3** | Stats + viz | `stats/*`, `viz/*`, selectors; sections 8–9 real | corroboration backends |
| **P4** | Skill mode complete + references | `llm/host.py`, all `references/*.md`, SKILL.md; host-LLM corroboration via packet; rule-based suggestions + host-LLM-enhancement path | CLI-mode LLM |
| **P5** | CLI-mode runners | `llm/base.py`, `llm/runners/{claude,gemini,codex,local}.py`, `utils/subprocess_runner.py`, `llm/prompts.py`; CLI-mode synthesis + corroboration + suggestions | web corroboration |
| **P6** | AI-slop + claim extraction + web corroboration | `validation/ai_slop.py`, `validation/claims.py`, `corroboration/{exa,brave,tavily}.py` with subprocess-runner mocks | — |
| **P7** | Second platform | Add adapter (TikTok or Reddit) with contract tests; prove zero core edits | — |
| **P8** | Perf + UX | `async` fetchers, richer terminal output, session replay polish | — |

Every phase ends green: tests + lint + a working demo command.

---

## 15. Verification

- **P1.** `srp update-topics --add '"a"|"b"'` → `topics.json` sorted, unique,
  `schema_version: 1`; duplicate add exits 3.
- **P2.** `srp run-research --mode skill --platform youtube '"ai agents"->trends'`
  prints a valid `SkillPacket(kind="synthesis", ...)` JSON including sections 1–7;
  exit 0.
- **P3.** Same command's packet includes real stats summary + chart paths on disk.
- **P4.** Skill-mode end-to-end: a test harness simulating Claude Code as host LLM
  reads the packet, follows `references/run-research.md`, and emits sections 1–11
  with sections 10/11 ≤150 words.
- **P5.** `srp run-research --mode cli --platform youtube '"ai agents"->trends'`
  (with `llm.runner=claude` and `claude` on PATH — or mocked in tests) emits
  sections 1–11 directly; subprocess failure falls back to sections 1–9 with
  warning.
- **P6.** `srp run-research --mode cli --corroboration exa '"ai agents"->trends'`
  (mocked) populates section 5 validated counts from Exa results.
- **P7.** Adding `platforms/reddit/` touches only that subpackage; contract suite
  and integration tests remain green.
- **Coverage.** `pytest --cov=src --cov-fail-under=85` passes.

---

## 16. Token-Saving Top 5

1. **Skill mode has zero external LLM calls.** Host LLM handles synthesis,
   suggestions, and corroboration inline from a compact packet.
2. **Per-subcommand reference loading.** SKILL.md loads ~40 lines; each invocation
   loads exactly one reference file.
3. **One synthesis call per research run.** Sections 10 + 11 combined into one
   schema; ≤150 words each.
4. **Top-5 cap before LLM.** Ranking/dedupe in code; LLM never sees candidate lists.
5. **Compact packet, not raw data.** ~1.5k-token JSON with ranked items + summaries
   + chart captions. No transcripts or API blobs reach any LLM.

## 17. Anti-LLM-Dependence Top 5

1. **Hand-rolled deterministic DSL parser.**
2. **Scoring is a formula with documented weights**, not a prompt.
3. **Model/chart selection is a lookup table + data-fit guard**, not a prompt.
4. **Dedupe uses `rapidfuzz`**, not "ask the LLM if these look similar".
5. **Migrations are version-chain pure functions**, not LLM-described transforms.

---

## 18. API Keys & Secrets

### Scope

Only **data-source** API keys are ever needed:

- `youtube_api_key` — required for the YouTube adapter.
- `exa_api_key` / `brave_api_key` / `tavily_api_key` — optional, only when the
  corresponding corroboration backend is selected.

**No LLM credentials are handled by `srp`**:
- Skill mode: host LLM does all LLM work (Hard Invariant #1).
- CLI mode: LLM CLI binaries (`claude`, `gemini`, `codex`, `ollama`) own their
  own auth via their own config/login flows. `srp` only invokes them.

### Storage & resolution order

1. **Process env var**: `SRP_<NAME>` uppercased
   (e.g. `SRP_YOUTUBE_API_KEY`, `SRP_EXA_API_KEY`).
2. **Secrets file**: `~/.social-research-probe/secrets.toml`, permissions `0600`,
   separate from `config.toml`. Format:
   ```toml
   [secrets]
   youtube_api_key = "..."
   exa_api_key     = "..."
   brave_api_key   = "..."
   tavily_api_key  = "..."
   ```
3. **Unset**: feature disabled with an actionable hint.

### `srp config` subcommand surface

```
srp config show                          # prints resolved config + secrets presence (values masked)
srp config path                          # prints the config/secrets file paths
srp config set <key> <value>             # writes to config.toml (non-secrets)
srp config set-secret <name> --from-stdin  # reads value from stdin, writes secrets.toml with 0600
srp config set-secret <name>             # prompts (hidden input) when interactive
srp config unset-secret <name>
srp config check-secrets [--needed-for <cmd>] [--platform NAME] [--corroboration NAME] [--output json]
```

`check-secrets` returns structured JSON:
```json
{"required": ["youtube_api_key"], "optional": ["exa_api_key"],
 "present":  ["exa_api_key"],     "missing":  ["youtube_api_key"]}
```

### Supported environments

| Environment | Shell access | Notes |
|---|---|---|
| **Terminal / CLI** | Full | Direct invocation; `srp config set-secret` works interactively or via `--from-stdin`. |
| **Claude Code** | Full (Bash tool) | Skill shells out via Bash tool; `srp` on `~/.local/bin` inherited from user PATH. |
| **Claude Cowork** | Full (local filesystem) | Confirmed: Cowork has full local filesystem and shell access — not sandboxed. Same as Claude Code. |

**All three environments require `srp` to be on PATH** (one-time: `pipx install social-research-probe`). The skill cannot self-install the CLI — if `srp` is not found, the host LLM should surface a clear "install srp first" message and stop.

### Secret setup — terminal only

API keys must be set from a terminal or shell. The host LLM must **never** ask the user to paste a secret value into chat.

**Skill-mode pre-flight (all environments):**

Each relevant reference file instructs the host LLM to:

1. Run `srp config check-secrets --needed-for <cmd> [--platform NAME] --output json`.
2. If `missing` is non-empty:
   - Display the required key names and where to obtain them.
   - Instruct the user to open a terminal and run:
     ```
     srp config set-secret <name>
     ```
     (The CLI will prompt with hidden input.)
   - Stop and wait; do not proceed until the user confirms the key is set.
3. On confirmation, re-run `check-secrets`; if still missing, surface the error and stop.
4. Proceed with the command.

Subsequent invocations find the key in `secrets.toml` and skip the pre-flight prompt entirely.

**Env-var alternative:** users may set `SRP_YOUTUBE_API_KEY` (or equivalent) as a process-level or launcher env var. Resolution order checks env first; the pre-flight then sees the key as present and skips the terminal prompt.

### Token budget estimates

Rough per-invocation token consumption when the skill is active (input + output combined):

| Scenario | Approx tokens |
|---|---|
| Skill listed, not triggered | ~300 (one-time, frontmatter only) |
| State commands (`show-topics`, `update-*`, `apply-pending`, etc.) | ~500–850 |
| Suggest commands (`suggest-topics`, `suggest-purposes`) | ~1,500–2,200 |
| `run-research` single topic × single purpose | ~3,700–5,400 |
| `run-research` multi-topic / multi-purpose | ~7,500–12,000 |

**Prompt-caching effect:** repeated static content (SKILL.md body, reference files, packet schema) qualifies for Anthropic prompt-caching (5-min TTL on Claude API). Warm-cache runs reduce input-token cost by ~75–90% on repeat invocations within the window. State commands benefit most; `run-research` sees smaller relative savings due to dynamic packet content.

### Security notes

- `secrets.toml` written with `os.umask(0o077)` + explicit `chmod 0600` immediately
  after create; verified on every read (warn if perms drifted).
- Values never echoed in logs, error messages, or packets sent to any LLM.
- `srp config show` masks all secret values (e.g., `youtube_api_key: sk-...abcd`).
- Tests assert redaction in every error path.

---

## Appendix A — Recommended CLI Shape

```
srp <noun>-<verb> [--flags] [positional]
```

Subcommands: `parse`, `show-topics`, `update-topics`, `show-purposes`,
`update-purposes`, `suggest-topics`, `suggest-purposes`, `show-pending`,
`apply-pending`, `discard-pending`, `stage-suggestions`, `run-research`,
`render-research`, `config` (with `show` / `path` / `set` / `set-secret` /
`unset-secret` / `check-secrets`), `corroborate-claims` (internal).

Global flags as listed in §9.

## Appendix B — Recommended Platform Adapter Shape

See §4 for full dataclasses and ABC. Registration via `@register` at module import.
Core reaches adapters only through `platforms.registry.get_adapter(name, config)`.

## Appendix C — Recommended LLM Runner Shape

See §5.2 for `LLMRunner` ABC. Each runner is a subprocess wrapper around an
existing LLM CLI (`claude`, `gemini`, `codex`, `ollama`). No Python SDK
dependencies. Pattern inspired by https://github.com/reshinto/gemini-skill.

## Appendix D — Post-Implementation Moves

After plan mode exits:

1. Move this file to `docs/superpowers/specs/2026-04-18-social-research-probe-design.md`
   in the project repo.
2. Commit as the initial design spec.
3. Invoke `superpowers:writing-plans` to produce a step-by-step implementation plan
   starting at Phase P0.
