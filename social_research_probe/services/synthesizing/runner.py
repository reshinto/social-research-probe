"""LLM-based synthesis orchestration and execution."""

from __future__ import annotations

from social_research_probe.services.llm.registry import get_runner
from social_research_probe.utils.core.errors import ValidationError
from social_research_probe.utils.core.flags import service_flag, stage_flag
from social_research_probe.utils.core.types import RunnerName
from social_research_probe.utils.display.progress import log

from .llm_contract import (
    SYNTHESIS_JSON_SCHEMA,
    build_synthesis_prompt,
    parse_synthesis_response,
)


def structured_runner_order(preferred: RunnerName) -> list[RunnerName]:
    """Return runner names with the preferred runner first."""
    candidates: list[RunnerName] = ["claude", "gemini", "codex", "local"]
    if preferred == "none":
        return []
    return [preferred, *[name for name in candidates if name != preferred]]


def run_required_synthesis(report: dict) -> dict | None:
    """Run LLM synthesis on report if enabled; return result or None."""
    if not stage_flag("synthesis", platform="youtube", default=True):
        log("[srp] synthesis: disabled (stages.synthesis = false).")
        return None
    if not service_flag("llm", default=True):
        log(
            "[srp] synthesis: disabled (services.llm = false). Enable the LLM service to allow synthesis."
        )
        return None
    from social_research_probe.config import load_active_config
    cfg = load_active_config()
    preferred = cfg.default_structured_runner
    if preferred == "none":
        log(
            "[srp] synthesis: disabled (llm.runner = 'none'). Set via 'srp config set llm.runner claude|gemini|codex|local'."
        )
        return None

    prompt = build_synthesis_prompt(report)
    failures: list[str] = []
    runners = structured_runner_order(preferred)
    for i, runner_name in enumerate(runners, start=1):
        if not cfg.technology_enabled(runner_name):
            log(f"[srp] synthesis: runner={runner_name} outcome=disabled_by_config")
            failures.append(f"{runner_name}: disabled by technologies.{runner_name}")
            continue
        log(f"[srp] synthesis: attempting runner {i}/{len(runners)} ({runner_name})")
        try:
            runner = get_runner(runner_name)
            if not runner.health_check():
                log(
                    f"[srp] synthesis: runner={runner_name} outcome=unavailable (binary not on PATH)"
                )
                failures.append(f"{runner_name}: unavailable")
                continue
            raw = runner.run(prompt, schema=SYNTHESIS_JSON_SCHEMA)
            result = parse_synthesis_response(raw)
            log(f"[srp] synthesis: runner={runner_name} outcome=success")
            return result
        except ValidationError as exc:
            log(f"[srp] synthesis: runner={runner_name} outcome=invalid_response err={exc}")
            failures.append(f"{runner_name}: invalid response ({exc})")
        except Exception as exc:
            log(f"[srp] synthesis: runner={runner_name} outcome=error err={exc}")
            failures.append(f"{runner_name}: {exc}")
    detail = "; ".join(failures) if failures else "no runners were attempted"
    log(
        "[srp] synthesis: all runners failed — "
        "Compiled Synthesis, Opportunity Analysis, and Final Summary will be omitted. "
        f"failures=[{detail}]"
    )
    return None


def attach_synthesis(report: dict) -> None:
    """Attach synthesis results to report (single or multi-report)."""
    children = report.get("multi")
    if isinstance(children, list):
        for child in children:
            synthesis = run_required_synthesis(child)
            if synthesis is not None:
                child.update(synthesis)
        return
    synthesis = run_required_synthesis(report)
    if synthesis is not None:
        report.update(synthesis)


def log_synthesis_runner_status() -> None:
    """Log synthesis runner availability status."""
    if not stage_flag("synthesis", platform="youtube", default=True):
        log("[srp] synthesis: disabled (stages.synthesis = false).")
        return
    if not service_flag("llm", default=True):
        log(
            "[srp] synthesis: disabled (services.llm = false). Enable the LLM service to allow synthesis."
        )
        return
    from social_research_probe.config import load_active_config
    preferred = load_active_config().default_structured_runner
    if preferred == "none":
        log(
            "[srp] synthesis: disabled (llm.runner = 'none'). Set via 'srp config set llm.runner claude|gemini|codex|local'."
        )
    else:
        runner = get_runner(preferred)
        if not runner.health_check():
            log(
                "[srp] synthesis: runner "
                f"'{preferred}' binary not found on PATH — synthesis will be skipped."
            )
