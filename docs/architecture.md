[Back to docs index](README.md)

# Architecture

This page explains the system from the problem it solves down to the runtime pipeline, module boundaries, and tradeoffs that shape the implementation.

![Architecture tree](images/architecture/architecture-tree.svg)

The diagram above is a top-down system tree. The person shape is the human
researcher. The document shape is command handling. The cloud shape is external
platform sources. The database cylinder is the local data directory. Rounded
process boxes represent pipeline and service work. This keeps the hierarchy
clear while making each kind of component visually distinct.

## Requirements

Functional requirements:

| Requirement | Implementation |
| --- | --- |
| Run research from a CLI | `srp research` in `cli/parsers.py` and `commands/research.py`. |
| Support platform-specific fetching | `platforms/youtube` stage modules and registry/client seams. |
| Rank items | `services/scoring` and `technologies/scoring`. |
| Enrich top results | transcript and summary services. |
| Corroborate claims | `services/corroborating` plus Exa, Brave, Tavily, and LLM search providers. |
| Produce reports | Markdown/HTML renderers, chart PNGs, optional audio. |

Non-functional requirements:

| Requirement | Design response | Tradeoff |
| --- | --- | --- |
| Cost control | Cache, top-N enrichment, local stats. | Cached evidence can remain until TTL expiry. |
| Extensibility | Platform, service, technology, and runner contracts. | More files than a single script. |
| Testability | Pure functions, fake platform seam, contract tests. | Requires keeping contracts documented and tested. |
| Local privacy | Config and artifacts remain local unless a provider is called. | Users must understand which optional services call external systems. |

![Component map](diagrams/components.svg)

## High-level design

The code is layered into distinct boundaries to keep components isolated and testable:

| Layer | Responsibility |
| --- | --- |
| CLI | Parse args, resolve data dir, dispatch command handlers. |
| Commands | User-facing operations such as research, config, topics, reports. |
| Platforms | Own platform-specific stage order and source adapters. |
| Services | Coordinate one task across inputs or technologies. |
| Technologies | Atomic vendor adapters or pure algorithms. |
| Utils | Cache, state, parsing, display, IO, validation. |

![System tradeoffs](diagrams/system-tradeoffs.svg)

### Platform, Service, and Technology Interaction

The core of the system is the relationship between Platforms, Services, and Technologies. 
- **Platforms** orchestrate the research process. They don't know *how* to transcribe or summarize, but they know *when* to ask for it.
- **Services** know how to execute a specific task (like fetching transcripts) concurrently across multiple inputs and handle fallbacks, but they don't know where the input came from.
- **Technologies** know how to do exactly one atomic thing (like calling the Whisper API or YouTube API). They don't know about pipelines or batch processing.

![Architecture interaction](diagrams/architecture_interaction.svg)

The layers intentionally point downward. Commands call platform orchestration. Platforms call services. Services call technologies. Technologies should not know about CLI commands or report pages. This keeps a provider integration from becoming tangled with user input parsing or final HTML rendering.

For example, the research command should not know how to call a transcript provider. It asks the platform pipeline to run. The platform pipeline asks the transcript service to enrich selected items. The transcript service calls one or more transcript technologies. That separation makes it possible to test each part and replace one provider without rewriting the whole command.

### Extending the Architecture

Because of this strict layering, extending the system is straightforward:
- **[Adding a platform](adding-a-platform.md)**: Add a new source (e.g., TikTok, Web Search). The platform adapter maps source-specific fields into the internal `RawItem` shape.
- **[Adding a service](adding-a-service.md)**: Add a new pipeline capability (e.g., Image Analysis) that coordinates one or multiple tools.
- **[Adding a technology](adding-a-technology.md)**: Add a new concrete implementation for a service (e.g., a new Reddit search endpoint or a new Anthropic Claude model).

## Data model

The central runtime object is `PipelineState`. Stages read from `state.inputs` and prior `stage_outputs`, then write their own output. The final assembled report is placed in `state.outputs["report"]`.

![Pipeline state pattern](diagrams/dp_pipeline.svg)

`PipelineState` is the shared notebook for one run. It avoids passing a growing list of positional arguments through every stage. A stage can read the fields it needs, add its result under a named key, and leave unrelated data alone.

The tradeoff is discipline. Stage output keys become a contract. If a scoring stage writes `scored_items`, later analysis and report stages expect that shape to stay stable. When changing a stage output, update tests and docs that describe the packet.

## Key tradeoffs

### Local-first vs managed service

Local-first keeps costs and artifacts under user control. It also means the user must install runner CLIs and optional tools such as `yt-dlp`, Whisper dependencies, or provider credentials.

### Filesystem cache vs database

A filesystem cache is transparent, portable, and simple to delete. It is less powerful for long-term analytics than a relational store. The repository currently favors simple repeat-run speed over historical trend storage.

### CLI runner adapters vs SDKs

Runner CLIs let users authenticate with the tools they already use and avoid hard SDK dependencies. The downside is subprocess parsing, timeouts, and CLI availability checks.

### Top-N enrichment vs full enrichment

Top-N enrichment controls cost and runtime. The tradeoff is recall: if the scoring model under-ranks a valuable item, that item may not get transcript, summary, or corroboration work.

## How to reason about new features

Ask three questions before placing new code:

| Question | Likely home |
| --- | --- |
| Is this user-facing command behavior? | `commands` and `cli`. |
| Is this source-specific fetching or stage order? | `platforms`. |
| Is this reusable pipeline work such as scoring, charts, or reports? | `services`. |
| Is this one concrete provider, parser, renderer, or algorithm? | `technologies`. |
| Is this generic support code with no product decision? | `utils`. |

This keeps the codebase extensible. A future TikTok adapter should add source-specific fetching under `platforms`, but it should not duplicate statistics, report rendering, or LLM runner logic.
