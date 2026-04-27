[Back to docs index](README.md)

# Synthesis Authoring

![Summary and synthesis flow](diagrams/summary-quality.svg)

Synthesis combines top-ranked items, statistics, chart captions, engagement summaries, and corroboration evidence into report sections. The HTML report command can also accept replacement text files for selected final sections.

The purpose of synthesis is to turn structured evidence into readable conclusions without hiding where those conclusions came from. A good synthesis should distinguish source claims, corroborated facts, statistical patterns, and human interpretation.

## Inputs

| Input | Source |
| --- | --- |
| Top-N items | score, transcript, summary, corroboration stages. |
| Statistics | `StatisticsService`. |
| Charts | `ChartsService` captions and PNG paths. |
| Evidence summary | synthesis formatter helpers. |
| Optional override files | `srp report --compiled-synthesis`, `--opportunity-analysis`, `--final-summary`. |

## Good authoring practice

Keep claims tied to cited items or corroboration evidence. Use statistics to qualify confidence rather than to overstate causality. When replacing generated sections, preserve the distinction between observed evidence and interpretation.

## When to override generated text

Override sections when the generated text is too generic, when you need a stricter editorial voice, or when a human reviewer has corrected the final interpretation. Do not override sections to hide weak evidence. If evidence is weak, say that directly and explain what is missing.

## Example structure

| Section | Good content |
| --- | --- |
| Compiled synthesis | What the top-ranked evidence says when read together. |
| Opportunity analysis | Where the topic has under-covered sources, emerging angles, or low-competition high-signal items. |
| Final summary | A concise conclusion that names confidence level and important caveats. |

When writing replacement text, avoid introducing new facts that are not present in the packet unless you clearly mark them as external human analysis. The report should remain auditable from its inputs.

## Practical editing checklist

Before accepting final synthesis, check:

| Check | Why it matters |
| --- | --- |
| Every strong claim has a source item or corroboration basis. | Prevents unsupported conclusions. |
| Statistics are described as signals, not proof. | Avoids overstating small or skewed datasets. |
| Caveats are preserved. | Keeps uncertainty visible to readers. |
| Platform scope is clear. | A YouTube run should not claim to represent every platform. |
| Human edits do not contradict packet evidence. | Keeps the report auditable. |
