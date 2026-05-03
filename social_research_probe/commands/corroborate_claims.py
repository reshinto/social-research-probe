"""commands/corroborate_claims.py — CLI command to corroborate a list of claims.

Takes a JSON file containing claim texts, extracts Claim objects, runs each
through one or more corroboration providers, and writes the aggregated results
to stdout or an output file.


Input JSON format::



Output JSON format::



Called by: cli._dispatch when args.command == 'corroborate-claims'.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from social_research_probe.config import load_active_config
from social_research_probe.services.corroborating import corroborate_claim
from social_research_probe.technologies.validation.claim_extractor import Claim
from social_research_probe.utils.core.exit_codes import ExitCode


def _validate_corroboration_config() -> None:
    """Raise ValidationError if corroboration stage or service is disabled.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _validate_corroboration_config()
        Output:
            None
    """
    from social_research_probe.utils.core.errors import ValidationError

    cfg = load_active_config()
    if hasattr(cfg, "service_enabled") and not cfg.service_enabled("corroboration"):
        raise ValidationError(
            "cannot corroborate claims: services.corroboration is false. "
            "Enable the corroboration service to use corroboration providers."
        )


def _load_claims(input_path: str) -> list[dict]:
    """Read and parse the claims JSON file. Returns the raw claims list.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        input_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _load_claims(
                input_path=Path("report.html"),
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    from social_research_probe.utils.core.errors import ValidationError

    try:
        with open(input_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValidationError(f"cannot read claims file: {exc}") from exc
    return data.get("claims", [])


def _run_corroboration(raw_claims: list[dict], providers: list[str]) -> list[dict]:
    """Corroborate all claims concurrently and return results.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        raw_claims: Claim text or claim dictionary being extracted, classified, reviewed, or
                    corroborated.
        providers: Provider names selected for corroboration, search, or fallback execution.

    Returns:
        List in the order expected by the next stage, renderer, or CLI formatter.

    Examples:
        Input:
            _run_corroboration(
                raw_claims={"text": "The model reduces latency by 30%."},
                providers=["AI safety"],
            )
        Output:
            [{"title": "Example", "url": "https://youtu.be/demo"}]
    """
    sem = asyncio.Semaphore(5)

    async def _corroborate_one(i: int, rc: dict) -> dict:
        """Corroborate one raw claim and keep its index for ordered output.

        Extraction, review, corroboration, and reporting all need the same claim shape.

        Args:
            i: Count, database id, index, or limit that bounds the work being performed.
            rc: Return code from a provider or runner process.

        Returns:
            Dictionary with stable keys consumed by downstream project code.

        Examples:
            Input:
                await _corroborate_one(
                    i=3,
                    rc={"enabled": True},
                )
            Output:
                {"enabled": True}
        """
        text = rc.get("text", "")
        source = rc.get("source_text", text)
        claim = Claim(text=text, source_text=source, index=i)
        async with sem:
            return await corroborate_claim(claim, providers)

    async def _gather_all() -> list[dict]:
        """Run claim corroboration tasks and return their results in input order.

        Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
        and service layers.

        Returns:
            List in the order expected by the next stage, renderer, or CLI formatter.

        Examples:
            Input:
                await _gather_all()
            Output:
                [{"title": "Example", "url": "https://youtu.be/demo"}]
        """
        return await asyncio.gather(*[_corroborate_one(i, rc) for i, rc in enumerate(raw_claims)])

    return asyncio.run(_gather_all())


def _write_output(results: list[dict], output_path: str | None) -> None:
    """Write corroboration results to file or stdout.

    Command helpers keep user-facing parsing, validation, and output formatting out of the pipeline
    and service layers.

    Args:
        results: Service or technology result being inspected for payload and diagnostics.
        output_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        None. The result is communicated through state mutation, file/database writes, output, or an
        exception.

    Examples:
        Input:
            _write_output(
                results=[ServiceResult(service_name="comments", input_key="demo", tech_results=[])],
                output_path=Path("report.html"),
            )
        Output:
            None
    """
    out = json.dumps({"results": results}, indent=2, ensure_ascii=False)
    if output_path:
        Path(output_path).write_text(out)
    else:
        sys.stdout.write(out + "\n")


def run(
    input_path: str,
    providers: list[str],
    output_path: str | None = None,
) -> int:
    """Load claims from a JSON file, corroborate each, and write results.

    This is the command boundary: argparse passes raw options in, and the rest of the application
    receives validated project data or a clear error.

    Args:
        input_path: Filesystem location used to read, write, or resolve project data.
        providers: Provider names selected for corroboration, search, or fallback execution.
        output_path: Filesystem location used to read, write, or resolve project data.

    Returns:
        Integer count, limit, status code, or timeout used by the caller.

    Examples:
        Input:
            run(
                input_path=Path("report.html"),
                providers=["AI safety"],
                output_path=Path("report.html"),
            )
        Output:
            5
    """
    _validate_corroboration_config()
    raw_claims = _load_claims(input_path)
    results = _run_corroboration(raw_claims, providers)
    _write_output(results, output_path)
    return ExitCode.SUCCESS
