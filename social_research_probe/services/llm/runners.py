"""LLM runner selection and ordering."""

from social_research_probe.utils.core.types import RunnerName


def prioritize_runner(candidates: list[RunnerName], preferred: RunnerName) -> list[RunnerName]:
    """Return runner names with the preferred runner first."""
    return [preferred, *[n for n in candidates if n != preferred]]
