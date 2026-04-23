"""Pipeline stages shim: StageExecutionContext is an alias for PipelineState."""

from social_research_probe.platform.state import PipelineState

StageExecutionContext = PipelineState

__all__ = ["StageExecutionContext"]
