[Back to docs index](README.md)

# LLM Reliability Harness

![Reliability harness](diagrams/reliability-harness.svg)

The eval tools run repeated LLM tasks and summarize variation. They are meant for development and release confidence, not for normal end-user research runs.

LLM features can fail in ways normal unit tests do not catch: output may be valid JSON but low quality, concise but incomplete, or different across repeated calls. The harness gives maintainers a way to inspect that variation before changing prompts or runner behavior.

## What it measures

| Check | Reason |
| --- | --- |
| Multiple samples | LLM output can vary across calls. |
| Optional judge model | Some quality checks need semantic review. |
| Length and coverage | Summaries should be concise but not omit key ideas. |
| Markdown report output | Failures need readable evidence. |

## Tradeoff

The harness costs time and runner calls. Use it when changing prompts, runner adapters, synthesis contracts, or summary behavior.

## How to use the results

Do not read one bad sample as proof that the entire prompt is broken. Look for patterns across samples: repeated omissions, unstable structure, hallucinated claims, or large quality differences between runners. A good prompt should be stable enough that the report shape and main evidence survive normal model variation.

If a change improves average quality but increases variance, treat that as a risk. Research reports need predictable evidence handling more than occasional excellent prose.

## When to run it

Run the harness when changing prompts, summary word limits, synthesis structure, JSON output contracts, runner adapters, or model selection defaults. It is usually unnecessary for pure cache, config, chart, or documentation changes.

The harness is deliberately separate from normal research runs because it repeats model calls. That repetition is useful for evaluating stability, but it can be slow and can spend runner or provider quota.
