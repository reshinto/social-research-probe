[Back to docs index](README.md)

# Adding A Technology

A **Technology** is the most granular, atomic unit of work in the Social Research Probe. It represents a single algorithm, a specific third-party API, a local ML model, or an external database query.

Technologies are orchestrated by **Services**. They do not know about the CLI, the reporting logic, or the platforms. They take a specific input, do one thing, and return an output.

![Service–Technology relationship](diagrams/service-technology.svg)

## Architecture

A Technology extends `BaseTechnology[TInput, TOutput]` from `social_research_probe.technologies`.

The base class provides:
- **Error isolation**: Exceptions are caught and logged so one failing API doesn't crash the run.
- **Timing metrics**: Execution time is automatically logged.
- **Feature flags**: The technology won't run if its `enabled_config_key` is set to `false`.
- **Health Checks**: A standard interface to verify credentials or dependencies.
- **Disk caching**: Transparent caching via `_cached_execute` when the class variable `cacheable` is `True`.

## Implementation Checklist

| Step | Action | Why |
| --- | --- | --- |
| 1 | Create the class | Inherit from `BaseTechnology[Input, Output]`. |
| 2 | Set class variables | Define `name`, `health_check_key`, `enabled_config_key`, and optionally `cacheable`. |
| 3 | Implement `_execute()` | Put the actual network request, parsing, or algorithm here. |
| 4 | Implement `health_check()` | Check for CLI dependencies or API keys. |

## Concrete Example

Let's add a new "Reddit Search" technology that a sourcing service could use.

### 1. Create the Technology

Create `social_research_probe/technologies/media_fetch/reddit.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import httpx
from social_research_probe.technologies import BaseTechnology, HealthCheckResult

@dataclass
class RedditSearchInput:
    query: str
    limit: int = 10

@dataclass
class RedditSearchOutput:
    posts: list[dict]

class RedditSearchTech(BaseTechnology[RedditSearchInput, RedditSearchOutput]):
    name = "reddit_search"
    health_check_key = "reddit"
    enabled_config_key = "technologies.reddit_search"

    async def _execute(self, data: RedditSearchInput) -> RedditSearchOutput:
        # 1. Perform the atomic action
        url = f"https://www.reddit.com/search.json?q={data.query}&limit={data.limit}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": "SRP/1.0"})
            response.raise_for_status()
            
            # 2. Parse and return structured output
            raw_data = response.json()
            posts = [child["data"] for child in raw_data.get("data", {}).get("children", [])]
            return RedditSearchOutput(posts=posts)

    async def health_check(self) -> HealthCheckResult:
        # Verify required configuration or network reachability
        return HealthCheckResult(
            key=self.health_check_key,
            healthy=True,
            message="Reddit API is reachable"
        )
```

### 2. Add Configuration

Register the new configuration flags in `social_research_probe/config.py` and `config.toml.example`:

```toml
[technologies.reddit_search]
enabled = true
# Add other keys like `api_key` if needed
```

## Best Practices

- **Keep it atomic.** A technology should not try to fetch, score, and summarize. It should only do one of those things.
- **Fail loud inside `_execute`.** You don't need to catch `httpx.RequestError` inside `_execute`. Let it raise. The `BaseTechnology` class catches all exceptions and logs them securely.
- **Use Dataclasses.** Pass a dataclass into `_execute` and return a dataclass. This keeps the type signatures strong and refactoring easy.
- **No Side Effects.** Do not write to the file system or modify global state inside a technology. Return data and let the caller manage state.
