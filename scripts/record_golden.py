#!/usr/bin/env python3
"""Record a real API response into ``tests/fixtures/golden/`` for replay.

Run manually — never in CI. Recorded payloads are checked into the repo
and played back via ``respx`` in the evidence test suite, so CI stays
offline and deterministic.

Secrets (``Authorization``, ``X-Api-Key``, ``X-Subscription-Token``, etc.) are
redacted from request + response before writing. Emails and credit-card
shaped strings in response bodies are redacted too.

Example:

    python scripts/record_golden.py \\
        --service brave \\
        --url 'https://api.search.brave.com/res/v1/web/search?q=GPT-4+release+date' \\
        --auth-env SRP_BRAVE_API_KEY \\
        --auth-header X-Subscription-Token \\
        --out brave_supported.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"

_SECRET_KEYS = (
    "authorization",
    "x-api-key",
    "x-subscription-token",
    "bearer",
    "api_key",
    "token",
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def _redact(obj):
    """Walk a JSON-serialisable object redacting obvious secrets in-place."""
    if isinstance(obj, dict):
        return {
            k: ("***REDACTED***" if k.lower() in _SECRET_KEYS else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str):
        out = _EMAIL_RE.sub("***EMAIL***", obj)
        out = _CARD_RE.sub("***CARD***", out)
        return out
    return obj


def _build_headers(auth_env: str | None, auth_header: str | None) -> dict[str, str]:
    """Assemble the auth header from env var if both args are supplied."""
    headers = {"User-Agent": "social-research-probe/golden-recorder"}
    if auth_env and auth_header:
        value = os.environ.get(auth_env)
        if not value:
            raise SystemExit(f"env var {auth_env!r} not set — export it before recording")
        headers[auth_header] = value
    return headers


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--service", required=True, help="service name; becomes subdir under golden/")
    p.add_argument("--url", required=True, help="absolute URL to hit")
    p.add_argument("--method", default="GET", help="HTTP method (default GET)")
    p.add_argument(
        "--json",
        dest="json_body",
        help="JSON body to POST (enables --method POST implicitly)",
    )
    p.add_argument("--auth-env", help="env var holding API key")
    p.add_argument("--auth-header", help="header name to carry the key")
    p.add_argument("--out", required=True, help="output filename, relative to the service dir")
    p.add_argument("--timeout", type=float, default=30.0)
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    headers = _build_headers(args.auth_env, args.auth_header)
    body = json.loads(args.json_body) if args.json_body else None
    method = "POST" if body is not None else args.method

    with httpx.Client(timeout=args.timeout) as client:
        resp = client.request(method, args.url, headers=headers, json=body)
        resp.raise_for_status()
        try:
            payload = resp.json()
        except json.JSONDecodeError as exc:
            print(f"response was not JSON: {exc}", file=sys.stderr)
            return 1

    redacted = _redact(payload)
    out_path = GOLDEN_ROOT / args.service / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
