[Back to docs index](README.md)


# Adding A Technology

A technology is the smallest executable adapter in the pipeline. It can call an API, invoke a CLI, render a file, run an algorithm, or write persistence records.

![Service technology](diagrams/service-technology.svg)

## Contract

Subclass `BaseTechnology`. Set `name`, `enabled_config_key`, and optionally `health_check_key` and `cacheable`. Implement `_execute(data)`.

```python
from typing import ClassVar
from social_research_probe.technologies import BaseTechnology

class ExampleTech(BaseTechnology[dict, dict]):
    name: ClassVar[str] = "example"
    enabled_config_key: ClassVar[str] = "example"
    health_check_key: ClassVar[str] = "example"

    async def _execute(self, data: dict) -> dict:
        return {"ok": True}
```

## Runtime Behavior

`execute()` checks `[technologies]`, logs when debug is enabled, uses cache if allowed, catches exceptions, and returns `None` for disabled or failed work.

Cache files are stored under `cache/technologies/<name>/`. Set `cacheable = False` for write operations, side-effect-only work, or anything that must run every time. `SQLitePersistTech` is an example.

## Health Checks

Override `health_check()` when availability depends on binaries, environment, API keys, or network setup. Runner and provider selection should use health checks before expensive calls when possible.

## Tests

Test enabled and disabled gates, cacheable behavior when relevant, failure returning `None`, output shape, and service integration.
