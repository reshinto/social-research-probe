# Usage Guide

[Home](README.md) → Usage

---

## Quickstart

```bash
pip install social-research-probe
srp config set-secret YOUTUBE_API_KEY
srp research "AI safety" "latest-news"
```

`srp` prints a Markdown summary to stdout and writes a self-contained HTML report to `~/.social-research-probe/reports/`. Open it in any browser.

---

## Core Concepts

### Topics

A topic is a search subject — e.g. `"AI safety"`, `"climate tech"`. Topics are registered in `~/.social-research-probe/topics.json` and reused across runs.

```bash
srp show-topics
srp update-topics --add "climate tech"
srp update-topics --remove "old-topic"
```

### Purposes

A purpose is a research intent — e.g. `"latest-news"`, `"emerging-research"`. Each purpose has a description that shapes how `srp` enriches queries and weights results.

```bash
srp show-purposes
srp update-purposes --add "emerging-research"="Track peer-reviewed preprints"
```

### Pending proposals

`suggest-topics` and `suggest-purposes` generate LLM-driven proposals that land in a pending queue. Review them before they take effect:

```bash
srp suggest-topics
srp show-pending
srp apply-pending          # accept all
srp discard-pending        # reject all
```

---

## Running Research

### Single topic, single purpose

```bash
srp research "AI agents" "latest-news"
```

### Multi-purpose (comma-separated)

```bash
srp research "AI agents" "latest-news,trends"
```

### Explicit platform

```bash
srp research youtube "AI agents" "latest-news"
```

### Natural-language query

When the argument looks like a question or sentence (no registered topic match), `srp` auto-classifies it into a topic and purpose using the configured LLM runner:

```bash
srp research "who is winning the LLM benchmarks race?"
```

Requires `llm.runner != none`.

### Excluding YouTube Shorts

```bash
srp research "AI agents" "latest-news" --no-shorts
```

---

## Reading the Report

After each run, `srp` prints:

```
[srp] HTML report: file:///~/.social-research-probe/reports/<filename>.html
```

The HTML report contains all 11 sections, embedded charts, and a built-in text-to-speech player. Sections 10–11 (Compiled Synthesis and Opportunity Analysis) are written inline if `llm.runner` is configured.

---

## Generating a Report After the Fact

To attach custom synthesis sections to an existing packet:

```bash
srp report \
  --packet ~/.social-research-probe/packets/my-packet.json \
  --synthesis-10 /tmp/s10.txt \
  --synthesis-11 /tmp/s11.txt \
  --out ~/Desktop/report.html
```

---

## Corroboration Modes

`srp` auto-corroborates the top-5 results by querying web-search backends. Configure via:

```bash
srp config set corroboration.backend host       # auto-discover available backends (default)
srp config set corroboration.backend exa        # force Exa only
srp config set corroboration.backend llm_cli    # use the configured LLM runner
srp config set corroboration.backend none       # disable corroboration
```

---

## Configuration

```bash
srp config show                             # print all settings
srp config set llm.runner claude            # set LLM runner
srp config set corroboration.backend host   # set corroboration mode
```

---

## Skill Bundle

After running `srp install-skill`, invoke `srp` from inside a Claude Code session:

```
/srp research "AI safety" "latest-news"
```

The skill shells out to the `srp` CLI and formats the output for chat. See `social_research_probe/skill/SKILL.md` for details.

---

## See also

- [Command Reference](commands.md) — full flag listing
- [Architecture](architecture.md) — pipeline internals
- [Security](security.md) — secret handling
