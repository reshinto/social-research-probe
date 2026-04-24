"""Research platform orchestration layer."""


async def run_all_platforms(state) -> object:
    """Run research across all registered platforms for the given state.

    Currently only the YouTube platform is implemented. ``state.platform_type``
    is updated to 'youtube' before delegation.
    """
    from social_research_probe.platforms.youtube.pipeline import YouTubePipeline

    state.platform_type = "youtube"
    return await YouTubePipeline().run(state)


def __getattr__(name: str):
    """Support lazy import of YouTubePipeline to avoid circular imports."""
    if name == "YouTubePipeline":
        from social_research_probe.platforms.youtube.pipeline import YouTubePipeline

        return YouTubePipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["YouTubePipeline", "run_all_platforms"]
