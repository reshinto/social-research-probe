[Back to docs index](README.md)


# Adding A Service

![Add service interaction](diagrams/add_service_interaction.svg)

A service coordinates one reusable task. It is the layer between platform stages and technology adapters.

## Contract

Subclass `BaseService`. Set `service_name` and `enabled_config_key`. Implement `_get_technologies()` and `execute_service(data, result)`.

Do not override `execute_batch()` or `execute_one()`. `BaseService.__init_subclass__()` rejects those overrides.

## Lifecycle

1. Stage calls `service.execute_batch(inputs)`.
2. Base service gathers `execute_one(input)` for every input.
3. `execute_one` checks the service gate.
4. The service shapes technology input with `_technology_input(data)` if overridden.
5. Technologies run concurrently unless `run_technologies_concurrently = False` or `_get_technologies()` returns `[None]`.
6. Base service builds `TechResult` records.
7. `execute_service(data, result)` converts raw adapter outputs into the service's normalized output.

## Minimal Shape

```python
from typing import ClassVar
from social_research_probe.services import BaseService, ServiceResult

class ExampleService(BaseService[dict, dict]):
    service_name: ClassVar[str] = "youtube.example"
    enabled_config_key: ClassVar[str] = "services.youtube.enriching.example"

    def _get_technologies(self) -> list[object]:
        return [ExampleTech()]

    async def execute_service(self, data: dict, result: ServiceResult) -> ServiceResult:
        output = next((tr.output for tr in result.tech_results if tr.success), None)
        if result.tech_results:
            result.tech_results[0].output = output or {}
        return result
```

## Tests

Test enabled behavior, disabled behavior, successful technology output, technology failure output, empty input behavior, and stage integration.
