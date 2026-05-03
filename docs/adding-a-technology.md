[Back to docs index](README.md)

# Adding A Technology

A technology is the smallest executable adapter in the project. It performs one provider call, one CLI invocation, one renderer action, one persistence write, or one pure algorithm.

![Service-Technology relationship](diagrams/service-technology.svg)

## Contract

Technologies inherit from `BaseTechnology[TInput, TOutput]` in `social_research_probe/technologies/__init__.py`.

Set these class variables:

| Variable | Meaning |
| --- | --- |
| `name` | Stable technology name used in logs and cache path. |
| `enabled_config_key` | Flat key under `[technologies]`; if false, `execute()` returns `None`. |
| `health_check_key` | Optional key used by health-check output. |
| `cacheable` | Defaults to `True`; set `False` for writes, non-idempotent work, or local state mutation. |

Implement `_execute(data)`. Do not catch every exception inside `_execute()` just to hide failures. `BaseTechnology.execute()` catches exceptions, logs a safe message, and returns `None`.

## Lifecycle

```text
service -> tech.execute(data)
  -> check [technologies].<enabled_config_key>
  -> check per-stage cache bypass
  -> read cache unless disabled
  -> await _execute(data)
  -> write cache if result is not None and cacheable
  -> return result or None
```

Cache entries live under `cache/technologies/<name>/`.

## Minimal Example

```python
from __future__ import annotations

from typing import ClassVar

import httpx

from social_research_probe.technologies import BaseTechnology, HealthCheckResult


class ExampleSearchTech(BaseTechnology[dict, list[dict]]):
    name: ClassVar[str] = "example_search"
    health_check_key: ClassVar[str] = "example_api_key"
    enabled_config_key: ClassVar[str] = "example_search"

    async def health_check(self) -> HealthCheckResult:
        from social_research_probe.commands.config import read_secret

        present = bool(read_secret("example_api_key"))
        return HealthCheckResult(
            key=self.health_check_key,
            healthy=present,
            message="configured" if present else "missing example_api_key",
        )

    async def _execute(self, data: dict) -> list[dict]:
        query = str(data.get("query") or "")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get("https://example.com/search", params={"q": query})
            response.raise_for_status()
            payload = response.json()
        return [
            {"title": str(row.get("title", "")), "url": str(row.get("url", ""))}
            for row in payload.get("results", [])
            if isinstance(row, dict)
        ]
```

Add the flat technology gate:

```toml
[technologies]
example_search = true
```

## When To Disable Caching

Use `cacheable = False` when `_execute()` writes files, mutates a database, sends audio to a playback service, or depends on wall-clock side effects. Current persistence technology uses this pattern because writing a run to SQLite must execute each time.

## Health Checks

Use health checks for credentials, binaries, or local services:

| Dependency | Health check should verify |
| --- | --- |
| API key | Secret or env var exists and is well-formed enough to try. |
| CLI runner | Binary is on `PATH` or configured path exists. |
| Local service | Base URL is reachable or clearly configured. |
| Pure algorithm | Usually always healthy. |

## Tests

Add tests for:

- Technology returns the normalized project shape.
- Disabled technology gate returns `None`.
- Exceptions inside `_execute()` are isolated by `execute()`.
- Cacheable technologies read/write expected cache entries when safe.
- Non-cacheable technologies do not use the cache.

## Rules

- Keep technologies atomic. Do not fetch, score, summarize, and report in one adapter.
- Normalize provider output before it leaves the technology.
- Do not parse CLI arguments in a technology.
- Do not decide stage order in a technology.
- Use typed dictionaries or plain dictionaries that match existing project shapes when the rest of the pipeline expects dictionaries.
