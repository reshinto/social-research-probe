"""Progress logging to stderr, gated by the debug technology-log switch.

The ``log`` function uses the same on/off gate as ``service_log`` (env
``SRP_LOGS`` or the config flag ``debug.technology_logs_enabled``). When the
gate is off the function is a silent no-op, so the CLI can reserve stdout for
the final report path.
"""

from __future__ import annotations

import functools
import inspect
import sys
import time
from contextlib import contextmanager
from dataclasses import fields, is_dataclass

from social_research_probe.utils.display.service_log import logs_enabled


def log(msg: str) -> None:
    """Print a [srp]-prefixed progress message to stderr when logs are enabled.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        msg: Message template or log text emitted for operator feedback.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            log(
                msg="AI safety",
            )
        Output:
            None
    """
    if not _enabled():
        return
    print(msg, file=sys.stderr)


@contextmanager
def timed_operation(msg: str):
    """Document the timed operation rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        msg: Message template or log text emitted for operator feedback.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            timed_operation(
                msg="AI safety",
            )
        Output:
            "AI safety"
    """
    try:
        start = time.time()
        yield
        elapsed = time.time() - start
        log(f"{msg} outcome=success elapsed={elapsed:.2f}s")
    except Exception as exc:
        elapsed = time.time() - start
        log(f"{msg} outcome=error elapsed={elapsed:.2f}s err={exc}")
        raise


def _enabled() -> bool:
    """Return True iff technology logs are on; resilient to config-load errors.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _enabled()
        Output:
            True
    """
    try:
        from social_research_probe.config import load_active_config

        cfg = load_active_config()
        flag = bool(getattr(cfg, "debug", {}).get("technology_logs_enabled", False))
    except Exception:
        flag = False
    return logs_enabled(flag)


def _compact_value(value: object, *, max_chars: int) -> str:
    """Return a bounded representation suitable for stderr progress logs.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.
        max_chars: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _compact_value(
                value="42",
                max_chars=3,
            )
        Output:
            "AI safety"
    """
    if _is_pipeline_state(value):
        value = _summarize_pipeline_state(value)
    elif _is_service_result(value):
        value = _summarize_service_result(value)
    elif is_dataclass(value) and not isinstance(value, type):
        value = _summarize_dataclass(value)
    elif isinstance(value, dict):
        value = _summarize_dict(value)
    elif isinstance(value, list | tuple):
        value = _summarize_sequence(value)

    rendered = repr(value)
    if len(rendered) <= max_chars:
        return rendered
    return f"{rendered[: max_chars - 3]}..."


def _is_pipeline_state(value: object) -> bool:
    """Return whether is pipeline state is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_pipeline_state(
                value="42",
            )
        Output:
            True
    """
    return (
        hasattr(value, "platform_type") and hasattr(value, "inputs") and hasattr(value, "outputs")
    )


def _summarize_pipeline_state(value: object) -> dict[str, object]:
    """Document the summarize pipeline state rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _summarize_pipeline_state(
                value="42",
            )
        Output:
            {"enabled": True}
    """
    outputs = getattr(value, "outputs", {})
    stages = outputs.get("stages", {}) if isinstance(outputs, dict) else {}
    return {
        "platform": getattr(value, "platform_type", ""),
        "topic": value.inputs.get("topic", "") if isinstance(value.inputs, dict) else "",
        "purposes": value.inputs.get("purpose_names", []) if isinstance(value.inputs, dict) else [],
        "stages_done": list(stages.keys()),
    }


def _is_service_result(value: object) -> bool:
    """Return whether is service result is true for the input.

    This shared utility keeps one parsing or normalization rule in a single place instead of letting
    call sites drift apart.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        True when the condition is satisfied; otherwise False.

    Examples:
        Input:
            _is_service_result(
                value="42",
            )
        Output:
            True
    """
    return (
        hasattr(value, "service_name")
        and hasattr(value, "input_key")
        and hasattr(value, "tech_results")
    )


def _summarize_service_result(value: object) -> dict[str, object]:
    """Document the summarize service result rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _summarize_service_result(
                value="42",
            )
        Output:
            {"enabled": True}
    """
    return {
        "service": value.service_name,
        "input_key": value.input_key,
        "tech_results": [
            {
                "tech": tr.tech_name,
                "success": tr.success,
                "output": _compact_value(tr.output, max_chars=240),
                "error": tr.error,
            }
            for tr in value.tech_results
        ],
    }


def _summarize_dict(value: dict[object, object]) -> dict[object, object]:
    """Document the summarize dict rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _summarize_dict(
                value="42",
            )
        Output:
            {"enabled": True}
    """
    return {key: _summarize_container_value(item) for key, item in value.items()}


def _summarize_sequence(value: list[object] | tuple[object, ...]) -> dict[str, object]:
    """Document the summarize sequence rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _summarize_sequence(
                value="42",
            )
        Output:
            {"enabled": True}
    """
    preview = [_summarize_container_value(item) for item in value[:3]]
    return {"type": type(value).__name__, "len": len(value), "preview": preview}


def _summarize_container_value(value: object) -> object:
    """Document the summarize container value rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            _summarize_container_value(
                value="42",
            )
        Output:
            "AI safety"
    """
    if isinstance(value, dict):
        summary: dict[str, object] = {"type": "dict", "keys": sorted(str(k) for k in value)}
        for key in ("id", "title", "url", "report_path"):
            if key in value:
                summary[key] = value[key]
        return summary
    if isinstance(value, list | tuple):
        return _summarize_sequence(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _summarize_dataclass(value)
    return value


def _summarize_dataclass(value: object) -> dict[str, object]:
    """Build the small payload that carries type through this workflow.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        value: Source text, prompt text, or raw value being parsed, normalized, classified, or sent
               to a provider.

    Returns:
        Dictionary with stable keys consumed by downstream project code.

    Examples:
        Input:
            _summarize_dataclass(
                value="42",
            )
        Output:
            {"enabled": True}
    """
    summary: dict[str, object] = {"type": type(value).__name__}
    for field in fields(value):
        summary[field.name] = _summarize_container_value(getattr(value, field.name))
    return summary


def _format_call_input(bound: inspect.BoundArguments, *, max_chars: int) -> str:
    """Format call input for display or files.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        bound: Bound function arguments captured for progress logging.
        max_chars: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized string used as a config key, provider value, or report field.

    Examples:
        Input:
            _format_call_input(
                bound="AI safety",
                max_chars=3,
            )
        Output:
            "AI safety"
    """
    values = {name: value for name, value in bound.arguments.items() if name not in {"self", "cls"}}
    value = next(iter(values.values())) if len(values) == 1 else values
    return _compact_value(value, max_chars=max_chars)


def log_with_time(
    msg: str,
    *,
    max_chars: int = 1200,
):
    """Document the log with time rule at the boundary where callers use it.

    This utility is shared across commands, services, and stages, so the rule lives here instead of
    being reimplemented differently at each call site.

    Args:
        msg: Message template or log text emitted for operator feedback.
        max_chars: Count, database id, index, or limit that bounds the work being performed.

    Returns:
        Normalized value needed by the next operation.

    Examples:
        Input:
            log_with_time(
                msg="AI safety",
                max_chars=3,
            )
        Output:
            "AI safety"
    """

    def decorator(func):
        """Document the decorator rule at the boundary where callers use it.

        This utility is shared across commands, services, and stages, so the rule lives here instead of
        being reimplemented differently at each call site.

        Args:
            func: Function being wrapped for timed progress logging.

        Returns:
            Normalized value needed by the next operation.

        Examples:
            Input:
                decorator(
                    func="AI safety",
                )
            Output:
                "AI safety"
        """

        def bound_args(*args, **kwargs):
            """Document the bound args rule at the boundary where callers use it.

            This utility is shared across commands, services, and stages, so the rule lives here instead of
            being reimplemented differently at each call site.

            Returns:
                Normalized value needed by the next operation.

            Examples:
                Input:
                    bound_args()
                Output:
                    "AI safety"
            """
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            return bound

        def format_msg(bound: inspect.BoundArguments):
            """Format msg for display or file output.

            This utility is shared across commands, services, and stages, so the rule lives here instead of
            being reimplemented differently at each call site.

            Args:
                bound: Bound function arguments captured for progress logging.

            Returns:
                Normalized value needed by the next operation.

            Examples:
                Input:
                    format_msg(
                        bound="AI safety",
                    )
                Output:
                    "AI safety"
            """
            return msg.format(**bound.arguments)

        def format_start(operation_msg: str, bound: inspect.BoundArguments) -> str:
            """Format start for display or files.

            This utility is shared across commands, services, and stages, so the rule lives here instead of
            being reimplemented differently at each call site.

            Args:
                operation_msg: Rendered operation label shown in progress output.
                bound: Bound function arguments captured for progress logging.

            Returns:
                Normalized string used as a config key, provider value, or report field.

            Examples:
                Input:
                    format_start(
                        operation_msg="AI safety",
                        bound="AI safety",
                    )
                Output:
                    "AI safety"
            """
            return (
                f"{operation_msg} input={_format_call_input(bound, max_chars=max_chars)} starting"
            )

        def format_success(operation_msg: str, result: object, elapsed: float) -> str:
            """Format success for display or files.

            This utility is shared across commands, services, and stages, so the rule lives here instead of
            being reimplemented differently at each call site.

            Args:
                operation_msg: Rendered operation label shown in progress output.
                result: Service or technology result being inspected for payload and diagnostics.
                elapsed: Numeric score, threshold, prior, or confidence value.

            Returns:
                Normalized string used as a config key, provider value, or report field.

            Examples:
                Input:
                    format_success(
                        operation_msg="AI safety",
                        result=ServiceResult(service_name="comments", input_key="demo", tech_results=[]),
                        elapsed=0.75,
                    )
                Output:
                    "AI safety"
            """
            base = f"{operation_msg} outcome=success elapsed={elapsed:.2f}s"
            return f"{base} output={_compact_value(result, max_chars=max_chars)}"

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                """Document the async wrapper rule at the boundary where callers use it.

                This utility is shared across commands, services, and stages, so the rule lives here instead of
                being reimplemented differently at each call site.

                Returns:
                    Normalized value needed by the next operation.

                Examples:
                    Input:
                        await async_wrapper()
                    Output:
                        "AI safety"
                """
                bound = bound_args(*args, **kwargs)
                operation_msg = format_msg(bound)
                log(format_start(operation_msg, bound))
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    log(format_success(operation_msg, result, time.time() - start))
                    return result
                except Exception as exc:
                    log(
                        f"{operation_msg} outcome=error elapsed={time.time() - start:.2f}s err={exc}"
                    )
                    raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Document the sync wrapper rule at the boundary where callers use it.

            This utility is shared across commands, services, and stages, so the rule lives here instead of
            being reimplemented differently at each call site.

            Returns:
                Normalized value needed by the next operation.

            Examples:
                Input:
                    sync_wrapper()
                Output:
                    "AI safety"
            """
            bound = bound_args(*args, **kwargs)
            operation_msg = format_msg(bound)
            log(format_start(operation_msg, bound))
            start = time.time()
            try:
                result = func(*args, **kwargs)
                log(format_success(operation_msg, result, time.time() - start))
                return result
            except Exception as exc:
                log(f"{operation_msg} outcome=error elapsed={time.time() - start:.2f}s err={exc}")
                raise

        return sync_wrapper

    return decorator
