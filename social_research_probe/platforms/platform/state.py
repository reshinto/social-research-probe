"""PipelineState: shared mutable context threaded through all pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _stage_enabled(cfg: object, platform: str, stage: str) -> bool:
    """Return True iff the named stage gate is enabled in config."""
    return cfg.stage_enabled(f"stages.{platform}.{stage}")  # type: ignore[union-attr]


def _service_enabled(cfg: object, platform: str, group: str, name: str) -> bool:
    """Return True iff the named service gate is enabled in config."""
    return cfg.service_enabled(f"services.{platform}.{group}.{name}")  # type: ignore[union-attr]


def _technology_enabled(cfg: object, name: str) -> bool:
    """Return True iff the named technology is enabled in config."""
    return cfg.technology_enabled(name)  # type: ignore[union-attr]


@dataclass
class PipelineState:
    """Shared context object passed through all platform stages.

    ``inputs`` holds pre-run parameters (adapter, limits, topic, etc.).
    ``outputs`` accumulates stage and service results keyed by stage name.
    """

    platform_type: str
    cfg: object
    cmd: object
    data_dir: Path
    cache: object | None
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

    @classmethod
    def from_stage_context(cls, ctx: object) -> PipelineState:
        """Build a PipelineState from a legacy StageExecutionContext."""
        state = cls(
            platform_type=getattr(getattr(ctx, "cmd", None), "platform", "youtube"),
            cfg=getattr(ctx, "cfg", None),
            cmd=getattr(ctx, "cmd", None),
            data_dir=getattr(ctx, "data_dir", Path(".")),
            cache=None,
        )
        for key in (
            "adapter",
            "platform_config",
            "limits",
            "topic",
            "purpose_names",
            "search_topic",
            "scoring_weights",
            "timings",
            "corroboration_backends",
        ):
            value = getattr(ctx, key, None)
            if value is not None:
                state.inputs[key] = value
        state.outputs.update(getattr(ctx, "outputs", {}))
        return state
