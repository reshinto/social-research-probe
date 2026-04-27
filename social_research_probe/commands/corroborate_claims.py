"""commands/corroborate_claims.py — CLI command to corroborate a list of claims.

Takes a JSON file containing claim texts, extracts Claim objects, runs each
through one or more corroboration providers, and writes the aggregated results
to stdout or an output file.

Input JSON format::

    {"claims": [{"text": "...", "source_text": "..."}, ...]}

Output JSON format::

    {"results": [<corroborate_claim output>, ...]}

Called by: cli._dispatch when args.command == 'corroborate-claims'.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from social_research_probe.config import load_active_config
from social_research_probe.services.corroborating.host import corroborate_claim
from social_research_probe.technologies.validation.claim_extractor import Claim
from social_research_probe.utils.core.exit_codes import ExitCode


def _validate_corroboration_config() -> None:
    """Raise ValidationError if corroboration stage or service is disabled."""
    from social_research_probe.utils.core.errors import ValidationError

    cfg = load_active_config()
    if hasattr(cfg, "service_enabled") and not cfg.service_enabled("corroboration"):
        raise ValidationError(
            "cannot corroborate claims: services.corroboration is false. "
            "Enable the corroboration service to use corroboration providers."
        )


def _load_claims(input_path: str) -> list[dict]:
    """Read and parse the claims JSON file. Returns the raw claims list."""
    from social_research_probe.utils.core.errors import ValidationError

    try:
        with open(input_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValidationError(f"cannot read claims file: {exc}") from exc
    return data.get("claims", [])


def _run_corroboration(raw_claims: list[dict], providers: list[str]) -> list[dict]:
    """Corroborate all claims concurrently and return results."""
    sem = asyncio.Semaphore(5)

    async def _corroborate_one(i: int, rc: dict) -> dict:
        text = rc.get("text", "")
        source = rc.get("source_text", text)
        claim = Claim(text=text, source_text=source, index=i)
        async with sem:
            return await corroborate_claim(claim, providers)

    async def _gather_all() -> list[dict]:
        return await asyncio.gather(*[_corroborate_one(i, rc) for i, rc in enumerate(raw_claims)])

    return asyncio.run(_gather_all())


def _write_output(results: list[dict], output_path: str | None) -> None:
    """Write corroboration results to file or stdout."""
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
    """Load claims from a JSON file, corroborate each, and write results."""
    _validate_corroboration_config()
    raw_claims = _load_claims(input_path)
    results = _run_corroboration(raw_claims, providers)
    _write_output(results, output_path)
    return ExitCode.SUCCESS
