"""PipelineState: shared mutable context threaded through all pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineState:
    """Shared context object passed through all platform stages.

    ``platform_config`` holds runtime configuration and CLI overrides.
    ``inputs`` holds the research query (topic, purposes).
    ``outputs`` accumulates stage results keyed by stage name.
    """

    platform_type: str
    cmd: object
    cache: object | None
    platform_config: dict = field(default_factory=dict)
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)

    def get_stage_output(self, stage: str) -> dict[str, object]:
        """Return the output dict for a named stage, or empty dict."""
        stages: dict = self.outputs.setdefault("stages", {})
        return stages.get(stage, {})

    def set_stage_output(self, stage: str, data: dict[str, object]) -> None:
        """Store the output dict for a named stage."""
        stages: dict = self.outputs.setdefault("stages", {})
        stages[stage] = data

    def get_service_output(self, service: str) -> object:
        """Return the service result entry for a named service, or None."""
        services: list = self.outputs.setdefault("services", [])
        for entry in services:
            if isinstance(entry, dict) and entry.get("service") == service:
                return entry
        return None

    def set_service_output(self, service: str, data: object) -> None:
        """Upsert the service result entry for a named service."""
        services: list = self.outputs.setdefault("services", [])
        for idx, entry in enumerate(services):
            if isinstance(entry, dict) and entry.get("service") == service:
                services[idx] = data
                return
        services.append(data)
