"""PipelineState: shared mutable context threaded through all pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineState:
    """Shared context object passed through all platform stages.

    ``platform_config`` holds runtime configuration and CLI overrides. ``inputs`` holds the research
    query (topic, purposes). ``outputs`` accumulates stage results keyed by stage name.

    Examples:
        Input:
            PipelineState
        Output:
            PipelineState(platform_type="youtube", cmd=None, cache=None)
    """

    platform_type: str
    cmd: object
    cache: object | None
    platform_config: dict = field(default_factory=dict)
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)

    def get_stage_output(self, stage: str) -> dict[str, object]:
        """Return the output dict for a named stage, or empty dict.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Args:
            stage: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                get_stage_output(
                    stage="comments",
                )
            Output:
                {"enabled": True}
        """
        stages: dict = self.outputs.setdefault("stages", {})
        return stages.get(stage, {})

    def set_stage_output(self, stage: str, data: dict[str, object]) -> None:
        """Store the output dict for a named stage.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Args:
            stage: Registry, config, or CLI name used to select the matching project value.
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                set_stage_output(
                    stage="comments",
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                None
        """
        stages: dict = self.outputs.setdefault("stages", {})
        stages[stage] = data

    def get_service_output(self, service: str) -> object:
        """Return the stored service output entry for a named service.

        Platform orchestration uses this contract to run different platforms without leaking platform-
        specific state into callers.

        Args:
            service: Registry, config, or CLI name used to select the matching project value.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                get_service_output(
                    service="summary",
                )
            Output:
                "AI safety"
        """
        services: list = self.outputs.setdefault("services", [])
        for entry in services:
            if isinstance(entry, dict) and entry.get("service") == service:
                return entry
        return None

    def set_service_output(self, service: str, data: object) -> None:
        """Upsert the service result entry for a named service.

        Platform orchestration code uses this contract to run different platforms without leaking
        platform-specific state into callers.

        Args:
            service: Registry, config, or CLI name used to select the matching project value.
            data: Input payload at this service, technology, or pipeline boundary.

        Returns:
            None. The result is communicated through state mutation, file/database writes, output, or an
            exception.

        Examples:
            Input:
                set_service_output(
                    service="summary",
                    data={"title": "Example", "url": "https://youtu.be/demo"},
                )
            Output:
                None
        """
        services: list = self.outputs.setdefault("services", [])
        for idx, entry in enumerate(services):
            if isinstance(entry, dict) and entry.get("service") == service:
                services[idx] = data
                return
        services.append(data)
