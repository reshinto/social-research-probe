"""Research platform orchestration layer."""

from social_research_probe.platform.youtube import YouTubePipeline


async def run_all_platforms(state) -> object:
    """Run research across all registered platforms for the given state.

    Currently only the YouTube platform is implemented. ``state.platform_type``
    is updated to 'youtube' before delegation.
    """
    state.platform_type = "youtube"
    return await YouTubePipeline().run(state)


__all__ = ["YouTubePipeline", "run_all_platforms"]
