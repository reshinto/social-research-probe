[Back to docs index](README.md)


# Source Classification

![Classification flow](diagrams/classifying_flow.svg)

The classification code assigns each source one of four strings from `VALID_CLASSES`: `primary`, `secondary`, `commentary`, or `unknown`.

## Providers

| Provider | Class | Behavior |
| --- | --- | --- |
| `heuristic` | `HeuristicClassifier` | Curated channel fragments, channel-name regexes, and title regexes. |
| `llm` | `LLMClassifier` | Uses the active free-text runner and a JSON schema. |
| `hybrid` | `HybridClassifier` | Heuristic first, LLM only when the heuristic returns `unknown`. |

The YouTube classify stage batches only items that need classification and updates both the `classify` stage output and the existing `fetch` output so later stages see the label.

## Heuristic Signals

The curated map includes known news and analysis channels. Name patterns classify words such as `news`, `official`, and `reporting` as primary signals; `explainer`, `analysis`, `review`, `tech`, `academy`, `learning`, and `tutorial` as secondary signals; and `podcast`, `react`, `show`, `talk`, and `rant` as commentary signals. Title patterns detect commentary words such as reaction and opinion.

## Config

`services.youtube.classifying.source_class` gates the service. `technologies.classifying` gates all classifier technologies. `services.youtube.classifying.provider` selects `heuristic`, `llm`, or `hybrid`.
