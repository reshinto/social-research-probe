"""Plain-English readings for raw statistical results.

The stats modules emit precise but jargon-heavy captions ("Pearson r between
trust and opportunity: -0.4453"). A reader who is not a statistician cannot
act on a number alone. This module attaches a one-line interpretation to
each result based on its name and value, so the rendered ``## 7. Statistics``
section reads like commentary, not a textbook table.
"""

from __future__ import annotations

from social_research_probe.technologies.statistics import StatResult


def explain(result: StatResult) -> str:
    """Return ``"<caption> — <plain-english reading>"`` for *result*.

    Falls back to the bare caption when no specific reading is known. Keeps the reading short (one
    clause) so it never overwhelms the original caption.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            explain(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
            )
        Output:
            "AI safety"
    """
    reading = _reading_for(result)
    return f"{result.caption} — {reading}" if reading else result.caption


def _reading_for(result: StatResult) -> str | None:
    """Choose the plain-English reading for a statistical result.

    Services turn platform items into adapter requests and normalize results so stages handle
    success, skip, and failure the same way.

    Args:
        result: Service or technology result being inspected for payload and diagnostics.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _reading_for(
                result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
            )
        Output:
            "AI safety"
    """
    name = result.name
    value = result.value
    if name == "growth_rate":
        return _growth_reading(value)
    if name == "slope":
        return _slope_reading(value)
    if name == "r_squared":
        return _r_squared_reading(value)
    if name == "pearson_r":
        return _pearson_reading(value)
    if name == "outlier_count":
        return _outlier_count_reading(value)
    if name == "outlier_fraction":
        return _outlier_fraction_reading(value)
    if name == "iqr":
        return "spread of the middle half — small means tightly clustered"
    if name == "range":
        return "max minus min — gap between best and worst"
    if name.startswith("stdev_"):
        return _stdev_reading(value)
    if name.startswith("mean_"):
        return "average value across the series"
    if name.startswith("median_"):
        return "middle value — robust to outliers"
    return None


def _growth_reading(value: float) -> str:
    """Describe a growth-rate value in plain language.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _growth_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    if abs(value) < 0.005:
        return "essentially flat from item to item"
    direction = "rising" if value > 0 else "falling"
    return f"average {direction} change of {abs(value):.1%} per step"


def _slope_reading(value: float) -> str:
    """Describe a regression slope in plain language.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _slope_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    if abs(value) < 0.001:
        return "no meaningful linear trend"
    direction = "increases" if value > 0 else "decreases"
    return f"each step {direction} the value by {abs(value):.4f}"


def _r_squared_reading(value: float) -> str:
    """Document the r squared reading rule at the boundary where callers use it.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _r_squared_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    if value >= 0.8:
        return f"strong fit — {value:.0%} of the variation is explained by the trend"
    if value >= 0.5:
        return f"moderate fit — {value:.0%} of variation explained"
    if value >= 0.2:
        return f"weak fit — only {value:.0%} explained, trend is noisy"
    return f"no real linear pattern ({value:.0%} explained)"


def _pearson_reading(value: float) -> str:
    """Document the pearson reading rule at the boundary where callers use it.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _pearson_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    magnitude = abs(value)
    if magnitude < 0.1:
        strength = "no meaningful correlation"
    elif magnitude < 0.3:
        strength = "weak correlation"
    elif magnitude < 0.7:
        strength = "moderate correlation"
    else:
        strength = "strong correlation"
    if magnitude < 0.1:
        return strength
    direction = (
        "the two metrics move together" if value > 0 else "when one rises, the other tends to fall"
    )
    return f"{strength} — {direction}"


def _outlier_count_reading(value: float) -> str:
    """Describe the outlier count in plain language.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _outlier_count_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    n = int(value)
    if n == 0:
        return "no extreme items — scores are homogeneous"
    return f"{n} item(s) sit far from the rest — review them for novelty or noise"


def _outlier_fraction_reading(value: float) -> str:
    """Describe the outlier fraction in plain language.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _outlier_fraction_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    if value == 0.0:
        return "0% — the dataset is well-behaved"
    return f"{value:.0%} of items are outliers"


def _stdev_reading(value: float) -> str:
    """Describe standard deviation in plain language.

    Services translate platform data into adapter calls and normalize the result so stages can
    handle success, skip, and failure consistently.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _stdev_reading(
                value="42",
            )
        Output:
            "AI safety"
    """
    if value < 0.05:
        return "tight clustering — values barely vary"
    if value < 0.2:
        return "moderate variation"
    return "wide spread — values differ substantially"
