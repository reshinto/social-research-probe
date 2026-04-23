"""commands/corroborate_claims.py — CLI command to corroborate a list of claims.

Takes a JSON file containing claim texts, extracts Claim objects, runs each
through one or more corroboration backends, and writes the aggregated results
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
from social_research_probe.corroboration.host import corroborate_claim
from social_research_probe.technologies.validation.claim_extractor import Claim


def run(
    input_path: str,
    backends: list[str],
    output_path: str | None = None,
) -> int:
    """Load claims from a JSON file, corroborate each, and write results.

    Reads a JSON file whose top-level key "claims" holds a list of objects
    with "text" and optional "source_text" fields. Each claim is wrapped in a
    Claim dataclass and passed to the corroboration host. The aggregated
    verdicts are written as JSON either to stdout or to output_path.

    Args:
        input_path: Path to the JSON file containing claims.
        backends: List of backend names to use (e.g. ['exa', 'llm_search']).
        output_path: If given, write JSON results here; otherwise print to
            stdout.

    Returns:
        Exit code (0 on success).

    Raises:
        ValidationError: If the input file is missing, unreadable, or is not
            valid JSON.
    """
    from social_research_probe.errors import ValidationError

    cfg = load_active_config()
    if hasattr(cfg, "stage_enabled") and not cfg.stage_enabled("corroborate"):
        raise ValidationError(
            "cannot corroborate claims: stages.corroborate is false. "
            "Enable the corroborate stage to use corroboration backends."
        )
    if hasattr(cfg, "service_enabled") and not cfg.service_enabled("corroboration"):
        raise ValidationError(
            "cannot corroborate claims: services.corroboration is false. "
            "Enable the corroboration service to use corroboration backends."
        )

    try:
        with open(input_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValidationError(f"cannot read claims file: {exc}") from exc

    raw_claims = data.get("claims", [])

    # Cap concurrent claim processing to avoid hammering external APIs.
    sem = asyncio.Semaphore(5)

    async def _corroborate_one(i: int, rc: dict) -> dict:
        text = rc.get("text", "")
        # Fall back to the claim text itself when no separate source is given,
        # so corroboration backends always have a non-empty source to check.
        source = rc.get("source_text", text)
        claim = Claim(text=text, source_text=source, index=i)
        async with sem:
            return await corroborate_claim(claim, backends)

    async def _gather_claims() -> list[dict]:
        return await asyncio.gather(
            *[_corroborate_one(i, rc) for i, rc in enumerate(raw_claims)],
        )

    results = asyncio.run(_gather_claims())

    out = json.dumps({"results": results}, indent=2, ensure_ascii=False)
    if output_path:
        Path(output_path).write_text(out)
    else:
        sys.stdout.write(out + "\n")
    return 0
