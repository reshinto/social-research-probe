[Back to docs index](README.md)


# Corroboration

![Corroboration flow](diagrams/corroboration_flow.svg)

Corroboration starts from extracted claim dictionaries. The research pipeline runs it after the `claims` stage. The standalone `corroborate-claims` command accepts a JSON file and writes evidence results without running the full pipeline.

## Providers

| Provider | Technology |
| --- | --- |
| `llm_search` | Runner-backed search provider. |
| `exa` | Exa HTTP provider. |
| `brave` | Brave Search HTTP provider. |
| `tavily` | Tavily HTTP provider. |

`CorroborationHostTech` is the host technology that selects providers according to config and budgets. It returns aggregate verdict fields that stages merge back into claims.

## Research Pipeline Path

```text
summary top-N -> ClaimExtractionService -> extracted_claims -> CorroborationService -> claim statuses -> narratives
```

## Standalone Input

```json
{
  "claims": [
    {"text": "Example claim", "source_text": "Paragraph containing the claim"}
  ]
}
```

## Reading Verdicts

Treat corroboration as evidence retrieval, not absolute truth. A `supported` result means the provider found matching evidence. A `contradicted` result means conflicting evidence was found. `inconclusive` means the provider did not return enough usable evidence under the current query, budget, and provider availability.
