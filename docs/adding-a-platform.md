[Back to docs index](README.md)

# Adding A Platform

A platform owns source-specific fetching, normalization, and stage order. YouTube is the current concrete platform. New platforms should reuse shared scoring, statistics, charts, claims, corroboration, synthesis, reporting, export, cache, and persistence whenever their data can be normalized into the project item shape.

![Platform contract](diagrams/add_platform_contract.svg)

## Contract

A platform needs:

| Piece | Purpose |
| --- | --- |
| Source technologies | Fetch raw records and metadata from the external source. |
| Sourcing service | Coordinate those source technologies and normalize failures. |
| Platform stages | Decide the stage order and map stage outputs into `PipelineState`. |
| Pipeline class | Implements `BaseResearchPlatform.stages()` and `run()`. |
| Config defaults | Adds platform limits, stages, service gates, and technology gates. |
| Tests | Fakes, stage tests, and at least one pipeline integration path. |

![Add platform flow](diagrams/add_platform_flow.svg)

## Normalized Item Shape

Shared scoring and reports expect item dictionaries with as many of these fields as the platform can provide:

| Field | Meaning |
| --- | --- |
| `id` | Stable platform/source identifier. |
| `url` | Human-openable source URL. |
| `title` | Source title or headline. |
| `description` | Source description or excerpt. |
| `channel` or `author_name` | Source publisher/creator. |
| `published_at` | `datetime` or ISO-like timestamp. |
| `source_class` | `primary`, `secondary`, `commentary`, or `unknown`. |
| `extras` | Provider-specific metadata used by scoring/reporting, such as subscriber count. |
| `scores` | Added by scoring. |
| `features` | Added by scoring. |
| `transcript`, `summary`, `text_surrogate` | Added by enrichment stages when applicable. |
| `extracted_claims`, `corroboration`, `narrative_ids` | Added by claims/corroboration/narrative stages. |

Engagement metrics should align with item order when passed into scoring. If a platform lacks views, likes, comments, or subscriber counts, leave them missing rather than inventing zeros.

## Minimal Platform Skeleton

```python
from __future__ import annotations

import asyncio

from social_research_probe.platforms import BaseResearchPlatform, BaseStage
from social_research_probe.platforms.state import PipelineState


class WebFetchStage(BaseStage):
    @property
    def stage_name(self) -> str:
        return "fetch"

    async def execute(self, state: PipelineState) -> PipelineState:
        if not self._is_enabled(state):
            state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
            return state
        topic = str(state.inputs.get("topic") or "")
        # Call a WebSourcingService here.
        state.set_stage_output("fetch", {"items": [], "engagement_metrics": []})
        return state


class WebPipeline(BaseResearchPlatform):
    def stages(self) -> list[list[BaseStage]]:
        return [
            [WebFetchStage()],
            # Reuse or adapt shared stages once item shape is compatible.
        ]

    async def run(self, state: PipelineState) -> PipelineState:
        for group in self.stages():
            if len(group) == 1:
                state = await group[0].run(state)
            else:
                await asyncio.gather(*(stage.run(state) for stage in group))
        return state
```

Register the concrete pipeline in `platforms/__init__.py` by extending `_get_concrete_pipelines()`.

## Reusing Shared Stages

| Shared behavior | Reuse when | Adapt or skip when |
| --- | --- | --- |
| Classification | Platform has source/channel/author identity. | Source type is not meaningful or needs a new classifier. |
| Scoring | Platform can provide item timestamps and engagement-like metrics. | Ranking logic needs platform-specific features first. |
| Transcript | Source is video/audio and a transcript technology exists. | Platform is text-first. |
| Comments | Platform has comments and an adapter exists. | Comments are unavailable or out of scope. |
| Summary/text surrogate | Items have enough text evidence for useful summaries. | Only metadata exists. |
| Claims/corroboration | Items contain checkable statements. | Output is only a navigation index. |
| Narratives | Claim extraction is enabled. | There are no structured claims. |
| Statistics/charts | Items have numeric score/features. | Result set is too small or nonnumeric. |
| Report/export/persist | Report packet matches `ResearchReport` shape. | New output shape requires renderer/export updates. |

## Config Checklist

Add platform defaults:

```python
DEFAULT_CONFIG["platforms"]["web"] = {
    "recency_days": 30,
    "max_items": 20,
    "enrich_top_n": 5,
}
DEFAULT_CONFIG["stages"]["web"] = {
    "fetch": True,
    "score": True,
    "report": True,
}
```

Add service and technology gates for any new service/adapter:

```python
DEFAULT_CONFIG["services"]["web"] = {
    "sourcing": {"web": True},
}
DEFAULT_CONFIG["technologies"]["web_search"] = True
```

Mirror user-facing keys in `config.toml.example` and update [Configuration](configuration.md) if the new platform is supported for users.

## Tests

| Test | Goal |
| --- | --- |
| Technology unit tests | Provider parsing and disabled-gate behavior. |
| Service unit tests | `ServiceResult` shape and partial failures. |
| Stage tests | Stage reads/writes the expected `PipelineState` keys. |
| Fake platform integration | Full pipeline with deterministic source-like data and no network. |
| Docs contract tests | Every new doc and diagram link resolves. |

## Common Mistakes

- Duplicating scoring, charts, reports, or persistence in a platform package instead of reusing shared layers.
- Passing raw provider responses past the technology boundary.
- Treating missing engagement as zero instead of unknown.
- Adding stage outputs without updating report/export/persistence consumers.
- Adding config keys to `config.toml.example` but not `DEFAULT_CONFIG`, or the reverse.
