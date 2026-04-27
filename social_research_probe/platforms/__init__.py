"""Platform adapters: base protocol, registry, and platform-specific implementations."""

_concrete_pipelines: dict[str, type] | None = None


def _get_concrete_pipelines() -> dict[str, type]:
    global _concrete_pipelines
    if _concrete_pipelines is None:
        import social_research_probe.services.sourcing.youtube  # registers YouTubeConnector
        from social_research_probe.platforms.youtube.pipeline import YouTubePipeline

        _concrete_pipelines = {"youtube": YouTubePipeline}
    return _concrete_pipelines


def __getattr__(name: str):
    if name == "PIPELINES":
        from social_research_probe.platforms.all.pipeline import AllPlatformsPipeline

        return {**_get_concrete_pipelines(), "all": AllPlatformsPipeline}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["PIPELINES"]
