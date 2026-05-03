[Back to docs index](README.md)

# Summary Quality

![Summary quality pipeline](diagrams/summary-quality.svg)

Summaries are generated only after transcript retrieval and only for top-N items. The summary service caches successful outputs by prompt/input so repeat runs do not pay again.

The summary layer exists to compress source material, not to invent missing evidence. If a transcript is unavailable or thin, the summary should be absent or cautious rather than confident.

## Quality goals

| Goal | Mechanism |
| --- | --- |
| Short summaries | `tunables.per_item_summary_words`. |
| Avoid empty output | runner failure returns no summary instead of crashing the pipeline. |
| Keep runs repeatable | summary technology cache under `cache/technologies/llm_ensemble`. |
| Detect weak evidence | assembly can report summary/transcript divergence warnings. |

## What to inspect

When a summary looks wrong, inspect the item's transcript, the active runner,
the `llm_ensemble` technology cache entry, and whether the item had enough
source text. If the runner is disabled, summaries may be absent while scoring,
stats, charts, and reports still work.

## Common failure modes

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| No summaries | Runner disabled, runner missing, or no transcript text. | Check `llm.runner`, runner CLI health, and transcript stage output. |
| Repeated generic summaries | Prompt/input too thin or cached weak output. | Inspect transcript text and clear the relevant `cache/technologies/llm_ensemble` entry if needed. |
| Summary contradicts transcript | Runner error or bad source text. | Compare summary with transcript and treat the item as low confidence. |
| Summary is too long | Word-limit tunable too high or runner ignored instruction. | Lower `tunables.per_item_summary_words` and inspect runner behavior. |

Good summaries should be specific enough to identify the source's main claim, short enough to scan in a report, and cautious when the transcript does not support a strong interpretation.
