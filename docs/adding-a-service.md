[Back to docs index](README.md)

# Adding A Service

A **Service** in the Social Research Probe coordinates a specific task (e.g., scoring, transcript fetching, summarizing) across one or multiple underlying **Technologies**. Services are called by **Platform Pipelines** and their job is to handle the concurrent execution of technologies, aggregate the results, and handle any tech-level failures gracefully.

## Architecture

![Add service interaction](diagrams/add_service_interaction.svg)

A Service extends `BaseService[TInput, TOutput]` from `social_research_probe.services.base`.

## Implementation Checklist

| Step | Action | Why |
| --- | --- | --- |
| 1 | Create the service class | Inherit from `BaseService`. Set `service_name` and `enabled_config_key`. |
| 2 | Implement `_get_technologies()` | Return the list of `BaseTechnology` instances this service should orchestrate. |
| 3 | Define input/output types | Use Dataclasses to keep a strict contract with the platform pipeline. |
| 4 | Add to pipeline | Call `await service.execute_batch(items)` from the appropriate pipeline stage. |

## Concrete Example

Let's say you want to add an "Image Analysis Service" that uses different AI vision models to analyze images.

### 1. Create the Service

Create `social_research_probe/services/image_analysis/__init__.py` and `service.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from social_research_probe.services.base import BaseService
from social_research_probe.technologies.base import BaseTechnology
from social_research_probe.technologies.vision.model_a import ModelATech
from social_research_probe.technologies.vision.model_b import ModelBTech

@dataclass
class ImageAnalysisInput:
    image_url: str
    context: str

@dataclass
class ImageAnalysisOutput:
    description: str
    tags: list[str]

class ImageAnalysisService(BaseService[ImageAnalysisInput, ImageAnalysisOutput]):
    service_name = "image_analysis"
    enabled_config_key = "services.image_analysis"

    def _get_technologies(self) -> list[BaseTechnology]:
        # Return the technologies you want to run. 
        # The base service handles executing them concurrently.
        return [
            ModelATech(),
            ModelBTech(),
        ]
```

### 2. Connect the Service in the Pipeline

In a platform pipeline stage (e.g., `platforms/instagram/pipeline.py`), instantiate and call the service:

```python
class InstagramAnalyzeStage(BaseStage):
    def stage_name(self) -> str:
        return "analyze_images"

    async def execute(self, state: PipelineState) -> PipelineState:
        items = state.get_stage_output("fetch").get("items", [])
        
        # Prepare inputs
        inputs = [ImageAnalysisInput(image_url=item.url, context=item.title) for item in items]
        
        # Run service
        service = ImageAnalysisService()
        results = await service.execute_batch(inputs)
        
        # Process ServiceResults
        # Each ServiceResult contains `tech_results` from Model A and Model B
        state.set_stage_output("analyze_images", {"results": results})
        return state
```

## Best Practices

- **Never put API keys or direct network calls in a Service.** A Service should only delegate to Technologies.
- **Fail gracefully.** `BaseService` automatically catches exceptions raised by a Technology. It returns `TechResult.success = False` rather than crashing the pipeline. Check `TechResult.output` before using it.
- **Isolate configuration.** Define a toggle for your service in `config.py` and `config.toml.example` so users can turn the entire service off.
